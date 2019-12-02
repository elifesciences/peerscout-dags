"""
dag for    extracting keywords from data in bbigquery
"""
import os
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import timedelta
from airflow import DAG
import airflow
from airflow.operators.python_operator import PythonOperator
from peerscout.keyword_extract.keyword_extract import etl_keywords
from peerscout.keyword_extract.keyword_extract_config \
    import KeywordExtractConfig, ExternalTriggerConfig

LOGGER = logging.getLogger(__name__)
DAG_ID = "Extract_Keywords_From_Corpus"

EXTRACT_KEYWORDS_SCHEDULE_INTERVAL_KEY = \
    "EXTRACT_KEYWORDS_SCHEDULE_INTERVAL_KEY"
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
    "destination_dataset": "placeholder",
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
    "limit_row_count_value": None
}

PEERSCOUT_DAG = DAG(
    dag_id=DAG_ID,
    default_args=get_default_args(),
    schedule_interval=get_env_var_or_use_default(
        EXTRACT_KEYWORDS_SCHEDULE_INTERVAL_KEY,
        DEFAULT_EXTRACT_KEYWORDS_SCHEDULE_INTERVAL,
    ),
    dagrun_timeout=timedelta(minutes=60),
)


def etl_extraction_keyword(**kwargs):
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

    with TemporaryDirectory() as tempdir:
        full_temp_file_location = Path.joinpath(
            Path(tempdir, "downloaded_rows_data")
        )
        keyword_extract_config = KeywordExtractConfig(
            DEFAULT_CONFIG, destination_dataset=dep_env,
            destination_table=table,
            limit_count_value=limit_row_count_value
        )
        etl_keywords(keyword_extract_config, full_temp_file_location)


def create_python_task(
        dag_name, task_id,
        python_callable, trigger_rule="all_success",
        retries=0
):
    """
    :param dag_name:
    :param task_id:
    :param python_callable:
    :param trigger_rule:
    :param retries:
    :return:
    """
    return PythonOperator(
        task_id=task_id,
        dag=dag_name,
        python_callable=python_callable,
        trigger_rule=trigger_rule,
        retries=retries,
    )


ETL_KEYWORD_EXTRACTION_TASK = create_python_task(
    PEERSCOUT_DAG, "etl_keyword_extraction_task",
    etl_extraction_keyword, retries=5
)
"""
def tas():
    print("TESTOMG")

task = PythonVirtualenvOperator(
            python_callable=tas,
            python_version=3.7,
            task_id='task',
            dag=PEERSCOUT_DAG)
"""
