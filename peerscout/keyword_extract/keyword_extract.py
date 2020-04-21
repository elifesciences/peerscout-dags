"""
utils for doing the heavy lifting job of extracting keywords
"""

import json
import re
import logging
from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Iterable, List
import datetime
from itertools import tee
from datetime import timezone
from abc import ABC, abstractmethod

from google.cloud.bigquery import WriteDisposition

import spacy
from spacy.language import Language

from peerscout.utils.bq_query_service import BqQuery
from peerscout.utils.bq_data_service import (
    load_file_into_bq,
    create_or_extend_table_schema
)
from peerscout.keyword_extract.keyword_extract_config import (
    KeywordExtractConfig
)

from peerscout.keyword_extract.spacy_keyword import (
    SpacyKeywordDocumentParser,
    DEFAULT_SPACY_LANGUAGE_MODEL_NAME
)

LOGGER = logging.getLogger(__name__)

SOURCE_TYPE_FIELD_NAME_IN_DESTINATION_TABLE = (
    "provenance_source_type"
)

# etl_state_timestamp given in this format primarily
# because datatime data returned from bigquery always
# has associated timezone
ETL_STATE_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S%z"
DATA_LOAD_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def to_unique_keywords(
        keywords: List[str],
        additional_keywords: List[str] = None) -> List[str]:
    return sorted(set(
        keywords + (additional_keywords or [])
    ))


class KeywordExtractor(ABC):
    @abstractmethod
    def iter_extract_keywords(
            self, text_list: Iterable[str]) -> Iterable[List[str]]:
        pass


class SimpleKeywordExtractor(KeywordExtractor):
    def iter_extract_keywords(
            self, text_list: Iterable[str]) -> Iterable[List[str]]:
        return (
            simple_regex_keyword_extraction(text)
            for text in text_list
        )


class SpacyKeywordExtractor(KeywordExtractor):
    def __init__(self, language: Language):
        self.parser = SpacyKeywordDocumentParser(language)

    def iter_extract_keywords(
            self, text_list: Iterable[str]) -> Iterable[List[str]]:
        return (
            document.get_keyword_str_list()
            for document in self.parser.iter_parse_text_list(text_list)
        )


def get_keyword_extractor(
        keyword_extract_config: KeywordExtractConfig) -> KeywordExtractor:

    extractor = SimpleKeywordExtractor()
    if keyword_extract_config.spacy_language_model:
        spacy_language_model_name = (
            keyword_extract_config.spacy_language_model
            or DEFAULT_SPACY_LANGUAGE_MODEL_NAME
        )
        extractor = SpacyKeywordExtractor(spacy.load(
            spacy_language_model_name
        ))
    return extractor


def etl_keywords_get_latest_state(
        keyword_extract_config: KeywordExtractConfig,
        timestamp_as_string: str,
        data_pipelines_state: dict = None,
):

    latest_state_value = data_pipelines_state.get(
        keyword_extract_config.pipeline_id,
        keyword_extract_config.default_start_timestamp
    )
    keyword_extractor = get_keyword_extractor(keyword_extract_config)
    bq_query_processing = BqQuery(
        project_name=keyword_extract_config.gcp_project)
    downloaded_data = download_data(
        bq_query_processing,
        " ".join([keyword_extract_config.query_template,
                  keyword_extract_config.limit_return_count]),
        keyword_extract_config.gcp_project,
        keyword_extract_config.source_dataset,
        latest_state_value
    )

    data_with_timestamp = add_timestamp(
        downloaded_data,
        keyword_extract_config.data_load_timestamp_field,
        timestamp_as_string,
    )
    data_with_provenance = add_provenance_source_type(
        data_with_timestamp,
        keyword_extract_config.provenance_fieldname_in_source_data,
        keyword_extract_config.provenance_value_from_config,
    )
    data_with_extracted_keywords = add_extracted_keywords(
        data_with_provenance,
        keyword_extract_config.text_field,
        keyword_extract_config.existing_keywords_field,
        keyword_extractor=keyword_extractor
    )

    with TemporaryDirectory() as tempdir:
        full_temp_file_location = Path.joinpath(
            Path(tempdir, "downloaded_rows_data"))
        latest_timestamp_iterator = (
            remove_cols_load_to_db_get_latest_timestamp(
                data_with_extracted_keywords, full_temp_file_location,
                keyword_extract_config
            )
        )

        if keyword_extract_config.state_timestamp_field:
            latest_state_value = get_latest_state(
                latest_timestamp_iterator
            )

    return latest_state_value


def current_timestamp_as_string():
    dtobj = datetime.datetime.now(timezone.utc)
    return dtobj.strftime(DATA_LOAD_TIMESTAMP_FORMAT)


def download_data(
        bq_query_processing, query_template, gcp_project, source_dataset,
        latest_state_value
) -> Iterable[dict]:

    rows = bq_query_processing.simple_query(
        query_template=query_template,
        gcp_project=gcp_project,
        dataset=source_dataset,
        latest_state_value=latest_state_value
    )
    return rows


def add_provenance_source_type(
        record_list,
        provenance_fieldname_in_source_data: str = None,
        provenance_value_from_config: str = None
):
    for record in record_list:
        record[SOURCE_TYPE_FIELD_NAME_IN_DESTINATION_TABLE] = (
            provenance_value_from_config or
            record.pop(provenance_fieldname_in_source_data, None)
        )
        yield record


def add_timestamp(record_list, timestamp_field_name, timestamp_as_string):
    for record in record_list:
        record[timestamp_field_name] = timestamp_as_string
        yield record


def get_latest_state(
        record_status_timestamp_list,
):
    latest_timestamp = datetime.datetime.strptime(
        "1900-01-10 00:00:00+0000",
        ETL_STATE_TIMESTAMP_FORMAT
    )
    for record_status_timestamp in record_status_timestamp_list:
        latest_timestamp = (
            latest_timestamp
            if latest_timestamp > record_status_timestamp
            else record_status_timestamp
        )
    return latest_timestamp


def remove_cols_load_to_db_get_latest_timestamp(
        json_list, full_temp_file_location,
        keyword_extract_config
):
    records_count = 0
    write_disposition = (
        WriteDisposition.WRITE_APPEND
        if keyword_extract_config.table_write_append
        else WriteDisposition.WRITE_TRUNCATE
    )
    with open(full_temp_file_location, "a") as write_file:
        for record in json_list:
            records_count += 1
            if records_count % 1000 == 0:
                load_data_to_bq(
                    keyword_extract_config,
                    full_temp_file_location,
                    write_disposition
                )
                write_file.truncate(0)
                LOGGER.info("%s records processed", str(records_count))
            latest_timestamp = record.pop(
                keyword_extract_config.state_timestamp_field
            )
            record.pop(keyword_extract_config.existing_keywords_field)
            record.pop(keyword_extract_config.text_field)
            record = {key: value for key, value in record.items() if value}
            write_file.write(json.dumps(record, ensure_ascii=False))
            write_file.write("\n")

            yield latest_timestamp

        load_data_to_bq(
            keyword_extract_config,
            full_temp_file_location,
            write_disposition
        )
        LOGGER.info("%s records processed", str(records_count))


def load_data_to_bq(
        keyword_extract_config,
        full_temp_file_location,
        write_disposition
):
    create_or_extend_table_schema(
        keyword_extract_config.gcp_project,
        keyword_extract_config.destination_dataset,
        keyword_extract_config.destination_table,
        full_temp_file_location
    )
    load_file_into_bq(
        filename=full_temp_file_location,
        table_name=keyword_extract_config.destination_table,
        auto_detect_schema=True,
        dataset_name=keyword_extract_config.destination_dataset,
        write_mode=write_disposition,
        project_name=keyword_extract_config.gcp_project
    )


def parse_keyword_list(keywords_str: str, separator: str = ","):
    if not keywords_str or not keywords_str.strip():
        return []
    return [
        keyword.strip()
        for keyword in keywords_str.split(separator)
    ]


def add_extracted_keywords(
        record_list: Iterable[dict],
        text_field: str,
        existing_keyword_field: str,
        keyword_extractor: KeywordExtractor,
        existing_keyword_split_pattern: str = ",",
        extracted_keyword_field_name: str = "extracted_keywords",
):
    text_record_list, record_list = tee(record_list, 2)
    text_list = (
        record.get(text_field, "")
        for record in text_record_list
    )
    text_keywords_list = keyword_extractor.iter_extract_keywords(text_list)
    for record, keywords in zip(record_list, text_keywords_list):
        additional_keywords = parse_keyword_list(
            record.get(existing_keyword_field, ""),
            separator=existing_keyword_split_pattern
        )
        new_keywords = to_unique_keywords(
            keywords,
            additional_keywords=additional_keywords
        )
        yield {
            **record,
            extracted_keyword_field_name: new_keywords
        }


def simple_regex_keyword_extraction(
        text: str,
        regex_pattern=r"([a-z](?:\w|-)+)"
):
    return re.findall(regex_pattern, text.lower())
