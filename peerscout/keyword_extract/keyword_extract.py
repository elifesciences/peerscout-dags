"""
utils for doing the heavy lifting job of extracting keywords
"""
import os
import json
import math
import re
import logging
from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Iterable, List, Tuple
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
from peerscout.utils.s3_data_service import (
    upload_s3_object
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

DEFAULT_BATCH_SIZE = 2000


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

    LOGGER.info(
        'loading keyword extractor, spacy language model: %s',
        keyword_extract_config.spacy_language_model
    )
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


def get_batch_count(total_count: int, batch_size: int) -> int:
    return math.floor((total_count + batch_size - 1) / batch_size)


# pylint: disable=too-many-locals
def etl_keywords(
        keyword_extract_config: KeywordExtractConfig,
        timestamp_as_string: str,
        state_s3_bucket: str = None,
        state_s3_object: str = None,
        data_pipelines_state: dict = None,
):

    LOGGER.info(
        'processing keyword extraction pipeline: %s (to %s.%s)',
        keyword_extract_config.pipeline_id,
        keyword_extract_config.destination_dataset,
        keyword_extract_config.destination_table
    )
    latest_state_value = data_pipelines_state.get(
        keyword_extract_config.pipeline_id,
        keyword_extract_config.default_start_timestamp
    )
    keyword_extractor = get_keyword_extractor(keyword_extract_config)
    bq_query_processing = BqQuery(
        project_name=keyword_extract_config.gcp_project)
    LOGGER.info(
        ' '.join([
            'retrieving data, source dataset: %s,'
            ' latest state value: %s (s3://%s/%s)'
        ]),
        keyword_extract_config.source_dataset,
        latest_state_value,
        state_s3_bucket,
        state_s3_object
    )
    downloaded_data, total_rows = download_data_and_get_total_rows(
        bq_query_processing,
        " ".join([keyword_extract_config.query_template,
                  keyword_extract_config.limit_return_count]),
        keyword_extract_config.gcp_project,
        keyword_extract_config.source_dataset,
        latest_state_value
    )
    batch_size = keyword_extract_config.batch_size or DEFAULT_BATCH_SIZE
    total_batch_count = get_batch_count(total_rows, batch_size)
    LOGGER.info(
        'total_rows: %d (batch size: %d, total batch count: %d)',
        total_rows, batch_size, total_batch_count
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

    write_disposition = (
        WriteDisposition.WRITE_APPEND
        if keyword_extract_config.table_write_append
        else WriteDisposition.WRITE_TRUNCATE
    )
    data_with_extracted_keywords_batches = iter_get_batches(
        data_with_extracted_keywords, batch_size
    )
    progress_monitor = 1
    for data_batch in data_with_extracted_keywords_batches:
        LOGGER.info(
            "uploading batch %d of %d (%.1f%%, batch size: %s)",
            progress_monitor,
            total_batch_count,
            (100.0 * progress_monitor / total_batch_count),
            batch_size
        )
        progress_monitor += 1
        latest_timestamp = get_latest_state(
            data_batch,
            keyword_extract_config.state_timestamp_field
        )
        with TemporaryDirectory() as tempdir:
            temp_processed_jsonl_path = os.fspath(
                Path(tempdir, "downloaded_rows_data")
            )
            write_to_jsonl_file(
                data_batch,
                temp_processed_jsonl_path,
                keyword_extract_config
            )
            load_data_to_bq(
                keyword_extract_config,
                temp_processed_jsonl_path,
                write_disposition
            )
        update_state(
            latest_timestamp,
            keyword_extract_config,
            data_pipelines_state,
            state_s3_bucket,
            state_s3_object
        )


def update_state(
        latest_timestamp,
        keyword_extract_config,
        state_dict,
        state_s3_bucket,
        state_s3_object
):
    if (
            keyword_extract_config.state_timestamp_field
            and latest_timestamp
    ):
        state_dict[keyword_extract_config.pipeline_id] = (
            latest_timestamp.strftime(ETL_STATE_TIMESTAMP_FORMAT)
        )
        state_as_string = json.dumps(
            state_dict, ensure_ascii=False, indent=4
        )
        upload_s3_object(
            bucket=state_s3_bucket,
            object_key=state_s3_object,
            data_object=state_as_string,
        )


def current_timestamp_as_string():
    dtobj = datetime.datetime.now(timezone.utc)
    return dtobj.strftime(DATA_LOAD_TIMESTAMP_FORMAT)


def download_data_and_get_total_rows(
        bq_query_processing, query_template, gcp_project, source_dataset,
        latest_state_value
) -> Tuple[Iterable[dict], int]:

    result = bq_query_processing.simple_query(
        query_template=query_template,
        gcp_project=gcp_project,
        dataset=source_dataset,
        latest_state_value=latest_state_value
    )
    return result, result.total_rows


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
        record_list,
        timestamp_field_name: str = None
):
    latest_timestamp = None
    if timestamp_field_name:
        timestamp_list = [
            record.get(timestamp_field_name)
            for record in record_list
            if record.get(timestamp_field_name)
        ]
        latest_timestamp = (
            max(timestamp_list) if timestamp_list else None
        )
    return latest_timestamp


def write_to_jsonl_file(
        data_with_extracted_keywords,
        full_temp_file_location,
        keyword_extract_config
):
    with open(full_temp_file_location, "w") as write_file:
        for record in data_with_extracted_keywords:
            record.pop(keyword_extract_config.existing_keywords_field, None)
            record.pop(keyword_extract_config.text_field, None)
            record.pop(keyword_extract_config.state_timestamp_field, None)
            record = {key: value for key, value in record.items() if value}
            write_file.write(json.dumps(record, ensure_ascii=False))
            write_file.write("\n")


def iter_get_batches(iterable, size):
    while True:
        chunk = []
        for _ in range(size):
            try:
                chunk.append(next(iterable))
            except StopIteration:
                yield chunk
                return
        yield chunk


def load_data_to_bq(
        keyword_extract_config,
        temp_processed_jsonl_path,
        write_disposition
):
    create_or_extend_table_schema(
        keyword_extract_config.gcp_project,
        keyword_extract_config.destination_dataset,
        keyword_extract_config.destination_table,
        temp_processed_jsonl_path
    )
    load_file_into_bq(
        filename=temp_processed_jsonl_path,
        table_name=keyword_extract_config.destination_table,
        auto_detect_schema=False,
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
