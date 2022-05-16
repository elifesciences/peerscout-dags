import os
import logging
import time
import yaml
from peerscout.utils.bq_query_service import BqQuery
from peerscout.keyword_extract.spacy_keyword import (
    DEFAULT_SPACY_LANGUAGE_MODEL_NAME
)
from peerscout.utils.s3_data_service import (
    delete_s3_object,
    download_s3_yaml_object_as_json
)
from peerscout.keyword_extract.keyword_extract_config import (
    MultiKeywordExtractConfig
)
from tests.end2end_test.end_to_end_test_helper import AirflowAPI

LOGGER = logging.getLogger(__name__)

AIRFLW_API = AirflowAPI()

EXTRACT_KEYWORDS_CONFIG_FILE_PATH_ENV_NAME = (
    "EXTRACT_KEYWORDS_FILE_PATH"
)
DATASET = "ci"
TABLE = "ci_extracted_keyword"


def get_pipeline_config():
    conf_file_path = os.getenv(
        EXTRACT_KEYWORDS_CONFIG_FILE_PATH_ENV_NAME
    )
    dep_env = (
        os.getenv(
            "DEPLOYMENT_ENV"
        )
    )
    with open(conf_file_path, 'r', encoding="UTF-8") as yaml_file:
        return MultiKeywordExtractConfig(
            yaml.safe_load(yaml_file),
            dep_env
        )


# pylint: disable=broad-except,too-many-locals
def test_dag_runs_data_imported(
        spacy_language_model_name=None
):
    multi_pipeline_config = get_pipeline_config()
    project_name = multi_pipeline_config.gcp_project
    spacy_language_model = (
        spacy_language_model_name or
        DEFAULT_SPACY_LANGUAGE_MODEL_NAME
    )
    state_file_bucket = multi_pipeline_config.state_file_bucket_name
    state_file_object = multi_pipeline_config.state_file_object_name
    bq_query_service = BqQuery(project_name=project_name)
    delete_statefile_if_exist(state_file_bucket,
                              state_file_object)
    conf_list = multi_pipeline_config.keyword_extract_config
    pipeline_with_state = [
        conf.get("pipelineID")
        for conf in conf_list
        if conf.get("stateTimestampField")
    ][0]
    pipeline_without_state = [
        conf.get("pipelineID")
        for conf in conf_list
        if not conf.get("stateTimestampField")
    ][0]
    try:
        LOGGER.info('cleaning table: %s.%s', DATASET, TABLE)
        bq_query_service.simple_query(
            query_template=TestQueryTemplate.CLEAN_TABLE_QUERY,
            gcp_project=project_name,
            dataset=DATASET,
            table=TABLE,
        )
    except Exception:
        LOGGER.info("table not cleaned, maybe it does not exist")

    dag_id = "Extract_Keywords_From_Corpus"
    config = {
        "dataset": DATASET,
        "table": TABLE,
        "limit_row_count_value": 5,
        "spacy_language_model": spacy_language_model,
        "state_file_bucket": state_file_bucket,
        "state_file_object": state_file_object
    }
    execution_date = AIRFLW_API.trigger_dag(dag_id=dag_id, conf=config)
    is_running = True
    while is_running:
        is_running = AIRFLW_API.is_dag_running(dag_id, execution_date)
        time.sleep(5)
        LOGGER.info("etl in progress")
    assert not is_running
    assert AIRFLW_API.get_dag_status(dag_id, execution_date) == "success"

    LOGGER.info('reading resuls from: %s.%s', DATASET, TABLE)
    query_response = bq_query_service.simple_query(
        query_template=TestQueryTemplate.READ_COUNT_TABLE_QUERY,
        gcp_project=project_name,
        dataset=DATASET,
        table=TABLE,
    )
    response = list(query_response)
    assert response[0].get("count") > 0

    etl_state = download_s3_yaml_object_as_json(
        state_file_bucket,
        state_file_object
    )
    assert len(etl_state) == 1
    assert pipeline_with_state in etl_state
    assert pipeline_without_state not in etl_state

    # clean up
    bq_query_service.simple_query(
        query_template=TestQueryTemplate.CLEAN_TABLE_QUERY,
        gcp_project=project_name,
        dataset=DATASET,
        table=TABLE,
    )
    delete_statefile_if_exist(
        state_file_bucket,
        state_file_object
    )


def delete_statefile_if_exist(
        state_file_bucket_name,
        state_file_object_name
):

    try:
        delete_s3_object(state_file_bucket_name,
                         state_file_object_name
                         )
    except Exception:
        LOGGER.info("s3 object not deleted, may not exist")


# pylint: disable=too-few-public-methods, missing-class-docstring
class TestQueryTemplate:
    CLEAN_TABLE_QUERY = """
    Delete from `{project}.{dataset}.{table}` where true
    """
    READ_COUNT_TABLE_QUERY = """
    Select Count(*) AS count from `{project}.{dataset}.{table}`
    """
