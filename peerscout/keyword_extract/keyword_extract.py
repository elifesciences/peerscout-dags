"""
utils for doing the heavy lifting job of extracting keywords
"""

import json
import re
from typing import Iterable, List
import datetime
from itertools import tee
from datetime import timezone
from abc import ABC, abstractmethod

from google.cloud.bigquery import WriteDisposition

import spacy
from spacy.language import Language

from peerscout.bq_utils.bq_query_service import BqQuery
from peerscout.bq_utils.bq_data_service import load_file_into_bq
from peerscout.keyword_extract.keyword_extract_config import (
    KeywordExtractConfig
)

from peerscout.keyword_extract.spacy_keyword import (
    SpacyKeywordDocumentParser,
    DEFAULT_SPACY_LANGUAGE_MODEL_NAME
)


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

    if not keyword_extract_config.spacy_language_model:
        return SimpleKeywordExtractor()
    else:
        spacy_language_model_name = (
            keyword_extract_config.spacy_language_model
            or DEFAULT_SPACY_LANGUAGE_MODEL_NAME
        )
        return SpacyKeywordExtractor(spacy.load(
            spacy_language_model_name
        ))


def etl_keywords(
        keyword_extract_config: KeywordExtractConfig,
        full_file_location: str,
        data_pipelines_state: dict = None
):
    latest_state_value = data_pipelines_state.get(
        keyword_extract_config.id_field
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
    downloaded_data, data_for_state_info_extraction = (
        tee(downloaded_data, 2)
    )
    if keyword_extract_config.data_load_timestamp_field:
        latest_state_value = get_latest_state(
            data_for_state_info_extraction,
            keyword_extract_config.data_load_timestamp_field,
            keyword_extract_config.state_timestamp_format
        )

    timestamp_as_string = current_timestamp_as_string()
    data_with_timestamp = add_timestamp(
        downloaded_data,
        keyword_extract_config.data_load_timestamp_field,
        timestamp_as_string,
    )
    data_with_extracted_keywords = add_extracted_keywords(
        data_with_timestamp,
        keyword_extract_config.text_field,
        keyword_extract_config.existing_keywords_field,
        keyword_extractor=keyword_extractor
    )
    write_to_file(data_with_extracted_keywords, full_file_location)
    write_disposition = (
        WriteDisposition.WRITE_APPEND
        if keyword_extract_config.table_write_append
        else WriteDisposition.WRITE_TRUNCATE
    )
    load_file_into_bq(
        filename=full_file_location,
        table_name=keyword_extract_config.destination_table,
        auto_detect_schema=True,
        dataset_name=keyword_extract_config.destination_dataset,
        write_mode=write_disposition,
        project_name=keyword_extract_config.gcp_project
    )

    if latest_state_value:
        data_pipelines_state[keyword_extract_config.pipeline_id] = (
            latest_state_value
        )

        state_as_string = json.dumps(
            data_pipelines_state, ensure_ascii=False, indent=4
        )
        upload_s3_object(
            bucket=state_file_bucket,
            object_key=state_file_name_key,
            data_object=latest_record_date,
        )



def current_timestamp_as_string():
    dtobj = datetime.datetime.now(timezone.utc)
    return dtobj.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_timestamp_from_string(
        timestamp_as_string: str,
        timestamp_format: str
):
    timestamp_obj = datetime.datetime.strptime(
        timestamp_as_string.strip(),
        timestamp_format
    )
    return timestamp_obj


def download_data(
        bq_query_processing, query_template, gcp_project, source_dataset,
        latest_state_value
) -> Iterable[dict]:

    rows = bq_query_processing.simple_query(
        query_template=query_template,
        gcp_project=gcp_project,
        source_dataset=source_dataset,
        latest_state_value=latest_state_value
    )
    return rows


def add_timestamp(record_list, timestamp_field_name, timestamp_as_string):
    for record in record_list:
        record[timestamp_field_name] = timestamp_as_string
        yield record


def get_latest_state(
        record_list,
        status_timestamp_field_name,
        timestamp_format
):
    latest_timestamp = datetime.datetime.min
    for record in record_list:
        record_status_timestamp =  get_timestamp_from_string(
            record.get(status_timestamp_field_name),
            timestamp_format
        )
        latest_timestamp = (
            latest_timestamp
            if latest_timestamp > record_status_timestamp
            else record_status_timestamp
        )
    return latest_timestamp


def write_to_file(json_list, full_temp_file_location):

    with open(full_temp_file_location, "a") as write_file:
        for record in json_list:
            write_file.write(json.dumps(record, ensure_ascii=False))
            write_file.write("\n")


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
    """
    :param text:
    :param regex_pattern:
    :return:
    """
    return re.findall(regex_pattern, text.lower())
