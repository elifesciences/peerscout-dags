"""
dag for    extracting keywords from data in bbigquery
"""
import os
import logging
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import timedelta
from airflow import DAG
import airflow
from airflow.operators.python_operator import PythonOperator
from peerscout.keyword_extract.keyword_extract import (
    etl_keywords
)
from peerscout.keyword_extract.utils import (
    get_yaml_file_as_dict
)
from peerscout.keyword_extract.keyword_extract_config import (
    KeywordExtractConfig, ExternalTriggerConfig
)

LOGGER = logging.getLogger(__name__)
DAG_ID = "Extract_Keywords_From_Corpus"

PEERSCOUT_CONFIG_FILE_PATH_ENV_NAME =\
    "PEERSCOUT_CONFIG_FILE_PATH"
EXTRACT_KEYWORDS_SCHEDULE_INTERVAL_ENV_NAME = \
    "EXTRACT_KEYWORDS_SCHEDULE_INTERVAL"
DEFAULT_EXTRACT_KEYWORDS_SCHEDULE_INTERVAL = None

DEPLOYMENT_ENV = "DEPLOYMENT_ENV"
DEFAULT_DEPLOYMENT_ENV_VALUE = None
EXTERNAL_TRIGGER_LIMIT_VALUE_KEY =\
    "limit_row_count_value"


def get_env_var_or_use_default(env_var_name, default_value):
    """
    :param env_var_name:
    :param default_value:
    :return:
    """
    return os.getenv(env_var_name, default_value)


def get_default_args():
    """
    :return:
    """
    return {
        "start_date": airflow.utils.dates.days_ago(1),
        "retries": 10,
        "retry_delay": timedelta(minutes=1),
        "retry_exponential_backoff": True,
        "provide_context": True,
    }


DEFAULT_CONFIG = {
    "gcp_project": "elife-data-pipeline",
    "source_dataset": "prod",
    "destination_dataset": "{ENV}",
    "destination_table": "extracted_keywords",
    "query_template": """
        WITH temp_t AS(
            SELECT
                name AS id,
                keywords AS keywords_csv,
                research_interests AS text_field,
                ROW_NUMBER() OVER (PARTITION BY name
                    ORDER BY imported_timestamp DESC) AS t
            FROM `{project}.{dataset}.public_editor_profile`
        )
        SELECT * EXCEPT(t) FROM temp_t
        WHERE t=1
                        """,
    "text_field": "text_field",
    "existing_keywords_field": "keywords_csv",
    "id_field": "id",
    "data_load_timestamp_field": "datahub_imported_timestamp",
    "table_write_append": "true",
    "limit_row_count_value": None,
    "spacy_language_model": "en_core_web_lg"
}

PEERSCOUT_DAG = DAG(
    dag_id=DAG_ID,
    default_args=get_default_args(),
    schedule_interval=get_env_var_or_use_default(
        EXTRACT_KEYWORDS_SCHEDULE_INTERVAL_ENV_NAME,
        DEFAULT_EXTRACT_KEYWORDS_SCHEDULE_INTERVAL,
    ),
    dagrun_timeout=timedelta(minutes=60),
)


def get_data_config(**kwargs):
    conf_file_path = get_env_var_or_use_default(
        PEERSCOUT_CONFIG_FILE_PATH_ENV_NAME, None
    )
    data_config_dict = copy.deepcopy(DEFAULT_CONFIG)
    if conf_file_path:
        data_config_dict.update(
            get_yaml_file_as_dict(conf_file_path)
        )
    kwargs["ti"].xcom_push(key="data_config_dict",
                           value=data_config_dict)


def etl_extraction_keyword(**kwargs):
    dag_context = kwargs["ti"]
    data_config_dict = dag_context.xcom_pull(
        key="data_config_dict", task_ids="get_data_config"
    )
    # handles the external triggers
    externally_triggered_parameters = kwargs['dag_run'].conf or {}
    limit_row_count_value = externally_triggered_parameters.get(
        ExternalTriggerConfig.LIMIT_ROW_COUNT
    )

    dep_env = (
        externally_triggered_parameters.get(
            ExternalTriggerConfig.BQ_DATASET_PARAM_KEY,
            get_env_var_or_use_default(DEPLOYMENT_ENV,
                                       DEFAULT_DEPLOYMENT_ENV_VALUE)
        )

    )
    table = externally_triggered_parameters.get(
        ExternalTriggerConfig.BQ_TABLE_PARAM_KEY
    )
    spacy_language_model = externally_triggered_parameters.get(
        ExternalTriggerConfig.SPACY_LANGUAGE_MODEL_NAME_KEY
    )

    with TemporaryDirectory() as tempdir:
        full_temp_file_location = Path.joinpath(
            Path(tempdir, "downloaded_rows_data")
        )
        keyword_extract_config = KeywordExtractConfig(
            data_config_dict, destination_dataset=dep_env,
            destination_table=table,
            limit_count_value=limit_row_count_value,
            spacy_language_model=spacy_language_model
        )
        etl_keywords(keyword_extract_config, full_temp_file_location)


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
    PEERSCOUT_DAG, "get_data_config", get_data_config, retries=5
)
ETL_KEYWORD_EXTRACTION_TASK = create_python_task(
    PEERSCOUT_DAG, "etl_keyword_extraction_task",
    etl_extraction_keyword, retries=5
)

# pylint: disable=pointless-statement
ETL_KEYWORD_EXTRACTION_TASK << GET_DATA_CONFIG_TASK
