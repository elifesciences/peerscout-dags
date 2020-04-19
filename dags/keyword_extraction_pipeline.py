import os
import logging
import json
import yaml
from tempfile import NamedTemporaryFile
from datetime import timedelta
from datetime import datetime
from airflow import DAG
import airflow
from airflow.models import Variable
from airflow.operators.python_operator import PythonOperator
from peerscout.keyword_extract.keyword_extract import (
    etl_keywords_get_latest_state,
    current_timestamp_as_string,
    ETL_STATE_TIMESTAMP_FORMAT
)
from peerscout.utils.s3_data_service import (
    get_stored_state,
    upload_s3_object
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

DEPLOYMENT_ENV = "DEPLOYMENT_ENV"


def get_default_args():
    return {
        "start_date": airflow.utils.dates.days_ago(1),
        "retries": 10,
        "retry_delay": timedelta(minutes=1),
        "retry_exponential_backoff": True,
        "provide_context": True,
    }


STATE_RESET_VARIABLE_NAME = (
    "peerscout_keyword_extraction_data_pipeline_state_reset"
)

PEERSCOUT_KEYWORD_EXTRACTION_DAG = DAG(
    dag_id=DAG_ID,
    default_args=get_default_args(),
    schedule_interval=os.getenv(
        EXTRACT_KEYWORDS_SCHEDULE_INTERVAL_ENV_NAME
    ),
    dagrun_timeout=timedelta(minutes=60),
)


def get_yaml_file_as_dict(file_location: str) -> dict:
    with open(file_location, 'r') as yaml_file:
        return yaml.safe_load(yaml_file)


def get_data_config(**kwargs):
    conf_file_path = os.getenv(
        EXTRACT_KEYWORDS_CONFIG_FILE_PATH_ENV_NAME
    )
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
        with NamedTemporaryFile() as named_temp_file:
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
                keyword_extract_config,
                state_dict,
                named_temp_file.name,
                timestamp_as_string,
                multi_keyword_extract_conf.state_file_bucket_name,
                multi_keyword_extract_conf.state_file_object_name
            )


def etl_and_update_state(
        keyword_extract_config: KeywordExtractConfig,
        state_dict: dict,
        temp_file_name: str,
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
    parsed_date_dict = {
        key: datetime.strptime(value, ETL_STATE_TIMESTAMP_FORMAT)
        for key, value in state_dict.items()
    }
    latest_state_value = etl_keywords_get_latest_state(
        keyword_extract_config,
        temp_file_name,
        timestamp_as_string,
        parsed_date_dict
    )
    if latest_state_value:
        state_dict[keyword_extract_config.pipeline_id] = (
            latest_state_value.strftime(ETL_STATE_TIMESTAMP_FORMAT)
        )
        state_as_string = json.dumps(
            state_dict, ensure_ascii=False, indent=4
        )
        upload_s3_object(
            bucket=state_file_bucket_name,
            object_key=state_file_object_name,
            data_object=state_as_string,
        )
    if to_reset_state:
        reset_var[keyword_extract_config.pipeline_id] = False
        Variable.set(
            STATE_RESET_VARIABLE_NAME,
            reset_var
        )


def create_python_task(
        dag_name, task_id,
        python_callable, trigger_rule="all_success",
        retries=0
):
    return PythonOperator(
        task_id=task_id,
        dag=dag_name,
        python_callable=python_callable,
        trigger_rule=trigger_rule,
        retries=retries,
    )


GET_DATA_CONFIG_TASK = create_python_task(
    PEERSCOUT_KEYWORD_EXTRACTION_DAG,
    "get_data_config", get_data_config, retries=5
)
ETL_KEYWORD_EXTRACTION_TASK = create_python_task(
    PEERSCOUT_KEYWORD_EXTRACTION_DAG,
    "etl_keyword_extraction_task",
    etl_extraction_keyword, retries=5
)

# pylint: disable=pointless-statement
ETL_KEYWORD_EXTRACTION_TASK << GET_DATA_CONFIG_TASK
