import logging
from peerscout.utils.bq_query_service import BqQuery
from peerscout.utils.s3_data_service import (
    delete_s3_object,
    download_s3_yaml_object_as_json
)
from peerscout.keyword_extract.keyword_extract_config import (
    KeywordExtractConfig
)

from peerscout.cli import main, get_multi_keyword_extract_config

LOGGER = logging.getLogger(__name__)


def test_dag_runs_data_imported():
    multi_pipeline_config = get_multi_keyword_extract_config()
    project_name = multi_pipeline_config.gcp_project
    state_file_bucket = multi_pipeline_config.state_file_bucket_name
    state_file_object = multi_pipeline_config.state_file_object_name
    bq_query_service = BqQuery(project_name=project_name)
    delete_statefile_if_exist(state_file_bucket,
                              state_file_object)
    conf_list = multi_pipeline_config.keyword_extract_config
    LOGGER.info('conf_list: %s', conf_list)
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
    first_config = KeywordExtractConfig(config=conf_list[0])
    dataset = first_config.destination_dataset
    table = first_config.destination_table
    assert dataset
    assert table
    try:
        LOGGER.info('cleaning table: %s.%s', dataset, table)
        bq_query_service.simple_query(
            query_template=TestQueryTemplate.CLEAN_TABLE_QUERY,
            gcp_project=project_name,
            dataset=dataset,
            table=table,
        )
    except Exception:  # pylint: disable=broad-except
        LOGGER.info("table not cleaned, maybe it does not exist")

    main()

    LOGGER.info('reading resuls from: %s.%s', dataset, table)
    query_response = bq_query_service.simple_query(
        query_template=TestQueryTemplate.READ_COUNT_TABLE_QUERY,
        gcp_project=project_name,
        dataset=dataset,
        table=table,
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
        dataset=dataset,
        table=table,
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
    except Exception:  # pylint: disable=broad-except
        LOGGER.info("s3 object not deleted, may not exist")


# pylint: disable=too-few-public-methods, missing-class-docstring
class TestQueryTemplate:
    CLEAN_TABLE_QUERY = """
    Delete from `{project}.{dataset}.{table}` where true
    """
    READ_COUNT_TABLE_QUERY = """
    Select Count(*) AS count from `{project}.{dataset}.{table}`
    """
