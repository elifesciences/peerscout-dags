"""
manages data config of the keyword extraction pipeline
"""
# pylint: disable=too-few-public-methods,simplifiable-if-expression,
# pylint: disable=too-many-arguments,too-many-instance-attributes


class KeywordExtractConfig:
    """
    manages data config of the keyword extraction pipeline
    """
    def __init__(
            self,
            config: dict,
            gcp_project: str = None,
            source_dataset: str = None,
            destination_dataset: str = None,
            destination_table: str = None,
            query_template: str = None,
            limit_count_value: int = None
    ):
        self.gcp_project = gcp_project or config.get("gcp_project")
        self.source_dataset = source_dataset or config.get("source_dataset")
        self.destination_dataset = destination_dataset or config.get(
            "destination_dataset"
        )
        self.destination_table = destination_table or config.get(
            "destination_table"
        )
        self.query_template = query_template or config.get("query_template")
        self.text_field = config.get("text_field")
        self.existing_keywords_field = config.get("existing_keywords_field")
        self.id_field = config.get("id_field")
        self.data_load_timestamp_field = config.get(
            "data_load_timestamp_field"
        )
        self.table_write_append = (
            True if config.get("table_write_append").lower() == "true"
            else False
        )
        limit_count = limit_count_value or config.get(
            "limit_row_count_value"
        )
        self.limit_return_count = " ".join(["Limit ", str(limit_count)]) \
            if limit_count else ""


class ExternalTriggerConfig:
    """
    configuration for external trigger parameter keys
    """
    LIMIT_ROW_COUNT = 'limit_row_count_value'
    BQ_DATASET_PARAM_KEY = 'dataset'
    BQ_TABLE_PARAM_KEY = 'table'
