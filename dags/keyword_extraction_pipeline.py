import os
import logging
from datetime import timedelta

import yaml
from airflow import DAG
import airflow
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.models.baseoperator import DEFAULT_QUEUE

from peerscout.keyword_extract.keyword_extract import (
    etl_keywords,
    current_timestamp_as_string
)
from peerscout.utils.s3_data_service import (
    get_stored_state,
)
from peerscout.keyword_extract.keyword_extract_config import (
    MultiKeywordExtractConfig,
    KeywordExtractConfig,
    ExternalTriggerConfig
)

LOGGER = logging.getLogger(__name__)
DAG_ID = "Extract_Keywords_From_Corpus"

EXTRACT_KEYWORDS_CONFIG_FILE_PATH_ENV_NAME = (
    "EXTRACT_KEYWORDS_FILE_PATH"
)
EXTRACT_KEYWORDS_SCHEDULE_INTERVAL_ENV_NAME = (
    "EXTRACT_KEYWORDS_SCHEDULE_INTERVAL"
)

EXTRACT_KEYWORDS_QUEUE_ENV_NAME = (
    "EXTRACT_KEYWORDS_QUEUE"
)

DEPLOYMENT_ENV = "DEPLOYMENT_ENV"


def get_default_args():
    return {
        "start_date": airflow.utils.dates.days_ago(1),
        "retries": 10,
        "retry_delay": timedelta(minutes=1),
        "retry_exponential_backoff": True
    }


STATE_RESET_VARIABLE_NAME = (
    "peerscout_keyword_extraction_data_pipeline_state_reset"
)

PEERSCOUT_KEYWORD_EXTRACTION_DAG = DAG(
    dag_id=DAG_ID,
    default_args=get_default_args(),
    schedule=os.getenv(
        EXTRACT_KEYWORDS_SCHEDULE_INTERVAL_ENV_NAME
    ),
    dagrun_timeout=timedelta(minutes=60),
)


def get_yaml_file_as_dict(file_location: str) -> dict:
    with open(file_location, 'r', encoding="UTF-8") as yaml_file:
        return yaml.safe_load(yaml_file)


def get_data_config(**kwargs):
    conf_file_path = os.environ[EXTRACT_KEYWORDS_CONFIG_FILE_PATH_ENV_NAME]
    data_config_dict = get_yaml_file_as_dict(
        conf_file_path
    )
    kwargs["ti"].xcom_push(
        key="multi_keyword_extract_conf_dict",
        value=data_config_dict
    )


def etl_extraction_keyword(**kwargs):
    dag_context = kwargs["ti"]
    multi_keyword_extract_conf_dict = dag_context.xcom_pull(
        key="multi_keyword_extract_conf_dict", task_ids="get_data_config"
    )
    # handles the external triggers
    externally_triggered_parameters = kwargs['dag_run'].conf or {}
    limit_row_count_value = externally_triggered_parameters.get(
        ExternalTriggerConfig.LIMIT_ROW_COUNT
    )
    dep_env = (
        externally_triggered_parameters.get(
            ExternalTriggerConfig.DEPLOYMENT_ENV,
            os.getenv(
                DEPLOYMENT_ENV
            )
        )
    )
    table = externally_triggered_parameters.get(
        ExternalTriggerConfig.BQ_TABLE_PARAM_KEY
    )
    spacy_language_model = externally_triggered_parameters.get(
        ExternalTriggerConfig.SPACY_LANGUAGE_MODEL_NAME_KEY
    )
    multi_keyword_extract_conf = MultiKeywordExtractConfig(
        multi_keyword_extract_conf_dict,
        dep_env
    )
    state_dict = get_stored_state(
        multi_keyword_extract_conf.state_file_bucket_name,
        multi_keyword_extract_conf.state_file_object_name
    )
    timestamp_as_string = current_timestamp_as_string()
    for extract_conf_dict in multi_keyword_extract_conf.keyword_extract_config:
        keyword_extract_config = KeywordExtractConfig(
            extract_conf_dict,
            gcp_project=multi_keyword_extract_conf.gcp_project,
            destination_table=table,
            limit_count_value=limit_row_count_value,
            spacy_language_model=spacy_language_model,
            import_timestamp_field_name=(
                multi_keyword_extract_conf.import_timestamp_field_name
            )
        )
        etl_and_update_state(
            keyword_extract_config=keyword_extract_config,
            state_dict=state_dict,
            timestamp_as_string=timestamp_as_string,
            state_file_bucket_name=multi_keyword_extract_conf.state_file_bucket_name,
            state_file_object_name=multi_keyword_extract_conf.state_file_object_name
        )


def etl_and_update_state(
        keyword_extract_config: KeywordExtractConfig,
        state_dict: dict,
        timestamp_as_string: str,
        state_file_bucket_name: str,
        state_file_object_name: str
):
    reset_var = (
        Variable.get(
            STATE_RESET_VARIABLE_NAME,
            {}
        )
    )

    to_reset_state = reset_var.get(
        keyword_extract_config.pipeline_id, False
    )
    if keyword_extract_config.state_timestamp_field and to_reset_state:
        state_dict[keyword_extract_config.pipeline_id] = (
            keyword_extract_config.default_start_timestamp
        )

    etl_keywords(
        keyword_extract_config=keyword_extract_config,
        timestamp_as_string=timestamp_as_string,
        state_s3_bucket=state_file_bucket_name,
        state_s3_object=state_file_object_name,
        data_pipelines_state=state_dict
    )
    if to_reset_state:
        reset_var[keyword_extract_config.pipeline_id] = False
        Variable.set(
            STATE_RESET_VARIABLE_NAME,
            reset_var
        )


def create_python_task(
        dag_name,
        task_id,
        python_callable,
        trigger_rule="all_success",
        retries=0,
        **kwargs
):
    return PythonOperator(
        task_id=task_id,
        dag=dag_name,
        python_callable=python_callable,
        trigger_rule=trigger_rule,
        retries=retries,
        **kwargs
    )


def get_queue() -> str:
    return os.getenv(
        EXTRACT_KEYWORDS_QUEUE_ENV_NAME,
        DEFAULT_QUEUE
    )


GET_DATA_CONFIG_TASK = create_python_task(
    PEERSCOUT_KEYWORD_EXTRACTION_DAG,
    "get_data_config",
    get_data_config,
    retries=5
)
ETL_KEYWORD_EXTRACTION_TASK = create_python_task(
    PEERSCOUT_KEYWORD_EXTRACTION_DAG,
    "etl_keyword_extraction_task",
    etl_extraction_keyword,
    retries=5,
    queue=get_queue()
)

# pylint: disable=pointless-statement
ETL_KEYWORD_EXTRACTION_TASK << GET_DATA_CONFIG_TASK
