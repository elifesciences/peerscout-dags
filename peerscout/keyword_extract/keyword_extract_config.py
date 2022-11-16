# pylint: disable=too-few-public-methods,simplifiable-if-expression,
# pylint: disable=too-many-arguments,too-many-instance-attributes


from typing import Optional


class MultiKeywordExtractConfig:
    def __init__(
            self,
            multi_keyword_extract_config: dict,
            deployment_env,
            deployment_env_placeholder: str = '{ENV}'
    ):
        updated_config = (
            update_deployment_env_placeholder(
                multi_keyword_extract_config,
                deployment_env,
                deployment_env_placeholder
            ) if deployment_env else multi_keyword_extract_config
        )
        self.gcp_project = updated_config.get(
            "gcpProjectName"
        )
        self.import_timestamp_field_name = updated_config.get(
            "importedTimestampFieldName"
        )
        self.state_file_bucket_name = updated_config.get(
            "stateFile", {}).get("bucketName")
        self.state_file_object_name = updated_config.get(
            "stateFile", {}).get("objectName")
        self.keyword_extract_config = (
            updated_config.get("keywordExtractionPipelines")
        )


class KeywordExtractConfig:
    def __init__(
            self,
            config: dict,
            gcp_project: Optional[str] = None,
            destination_table: Optional[str] = None,
            query_template: Optional[str] = None,
            limit_count_value: Optional[int] = None,
            spacy_language_model: Optional[str] = None,
            import_timestamp_field_name: Optional[str] = None
    ):
        self.pipeline_id = config.get("pipelineID")
        self.default_start_timestamp = config.get(
            "defaultStartTimestamp"
        )
        provenance_val = (
            config.get("provenance", {}).get(
                "value"
            )
        )
        provenance_type = (
            config.get("provenance", {}).get(
                "type"
            )
        )
        self.provenance_fieldname_in_source_data = (
            provenance_val
            if provenance_val
            and provenance_type == "sourceDataFieldName"
            else None
        )

        self.provenance_value_from_config = (
            provenance_val
            if provenance_val
            and provenance_type != "sourceDataFieldName"
            else None
        )

        self.gcp_project = gcp_project or config.get("gcpProjectName")
        self.source_dataset = config.get("sourceDataset")
        self.destination_dataset = config.get(
            "destinationDataset"
        )
        self.destination_table = destination_table or config.get(
            "destinationTable"
        )
        self.query_template = query_template or config.get("queryTemplate")
        self.text_field = config.get("textField")
        self.state_timestamp_field = config.get("stateTimestampField")
        self.existing_keywords_field = config.get("existingKeywordsField")
        self.id_field = config.get("idField")
        self.data_load_timestamp_field = (
            import_timestamp_field_name or
            config.get(
                "importedTimestampFieldName"
            )
        )
        self.table_write_append = (
            True if config.get("tableWriteAppend").lower() == "true"
            else False
        )
        limit_count = limit_count_value or config.get(
            "limitRowCountValue"
        )
        self.limit_return_count = " ".join(["Limit ", str(limit_count)]) \
            if limit_count else ""
        self.batch_size = config.get("batchSize")
        self.spacy_language_model = (
            spacy_language_model or config.get("spacyLanguageModel")
        )


class ExternalTriggerConfig:
    LIMIT_ROW_COUNT = 'limit_row_count_value'
    BQ_TABLE_PARAM_KEY = 'table'
    DEPLOYMENT_ENV = 'dep_env'
    SPACY_LANGUAGE_MODEL_NAME_KEY = 'spacy_language_model'


def update_deployment_env_placeholder(
        original_dict: dict,
        deployment_env: str,
        environment_placeholder: str,
):
    new_dict = {}
    for key, val in original_dict.items():
        if isinstance(val, dict):
            tmp = update_deployment_env_placeholder(
                val,
                deployment_env,
                environment_placeholder
            )
            new_dict[key] = tmp
        elif isinstance(val, list):
            new_dict[key] = [
                update_deployment_env_placeholder(
                    x,
                    deployment_env,
                    environment_placeholder
                )
                for x in val
            ]
        else:
            new_dict[key] = replace_env_placeholder(
                original_dict[key],
                deployment_env,
                environment_placeholder
            )
    return new_dict


def replace_env_placeholder(
        param_value,
        deployment_env: str,
        environment_placeholder: str
):
    new_value = param_value
    if isinstance(param_value, str):
        new_value = param_value.replace(
            environment_placeholder,
            deployment_env
        )
    return new_value
