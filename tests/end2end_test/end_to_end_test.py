import logging
import time
from peerscout.bq_utils.bq_query_service import BqQuery
from peerscout.keyword_extract.spacy_keyword import (
    DEFAULT_SPACY_LANGUAGE_MODEL_NAME
)
from tests.end2end_test.end_to_end_test_helper import AirflowAPI

LOGGER = logging.getLogger(__name__)

AIRFLW_API = AirflowAPI()
DATASET = "ci"
TABLE = "ci_extracted_keyword"
PROJECT = "elife-data-pipeline"  # change  all to env variable


# pylint: disable=broad-except
def test_dag_runs_data_imported(
        dataset: str = None, table: str = None,
        project: str = None,
        spacy_language_model_name=None
):
    """
    :return:
    """
    project_name = project or PROJECT
    dataset_name = dataset or DATASET
    table_name = table or TABLE
    spacy_language_model = (
        spacy_language_model_name or
        DEFAULT_SPACY_LANGUAGE_MODEL_NAME
    )
    bq_query_service = BqQuery(project_name=project_name)

    try:
        bq_query_service.simple_query(
            query=TestQueryTemplate.CLEAN_TABLE_QUERY,
            project=project_name,
            dataset=dataset_name,
            table=table_name,
        )
    except Exception:
        LOGGER.info("table not cleaned, maybe it does not exist")
    dag_id = "Extract_Keywords_From_Corpus"
    config = {
        "dataset": dataset_name,
        "table": table_name,
        "limit_row_count_value": 5,
        "spacy_language_model": spacy_language_model
    }
    execution_date = AIRFLW_API.trigger_dag(dag_id=dag_id, conf=config)
    is_running = True
    while is_running:
        is_running = AIRFLW_API.is_dag_running(dag_id, execution_date)
        time.sleep(5)
        LOGGER.info("etl in progress")
    assert not is_running
    assert AIRFLW_API.get_dag_status(dag_id, execution_date) == "success"

    query_response = bq_query_service.simple_query(
        query=TestQueryTemplate.READ_COUNT_TABLE_QUERY,
        project=project_name,
        dataset=dataset_name,
        table=table_name,
    )
    assert query_response[0].get("count") > 0

    # clean up
    bq_query_service.simple_query(
        query=TestQueryTemplate.CLEAN_TABLE_QUERY,
        project=project_name,
        dataset=dataset_name,
        table=table_name,
    )


# pylint: disable=too-few-public-methods, missing-class-docstring
class TestQueryTemplate:
    CLEAN_TABLE_QUERY = """
    Delete from `{project}.{dataset}.{table}` where true
    """
    READ_COUNT_TABLE_QUERY = """
    Select Count(*) AS count from `{project}.{dataset}.{table}`
    """
