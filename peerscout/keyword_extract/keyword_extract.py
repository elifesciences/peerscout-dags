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
    keyword_extractor_name = (
        keyword_extract_config.keyword_extractor or 'spacy'
    )
    if keyword_extractor_name == 'simple':
        return SimpleKeywordExtractor()
    if keyword_extractor_name == 'spacy':
        spacy_language_model_name = (
            keyword_extract_config.spacy_language_model
            or DEFAULT_SPACY_LANGUAGE_MODEL_NAME
        )
        return SpacyKeywordExtractor(spacy.load(
            spacy_language_model_name
        ))
    raise ValueError(
        'unsupported keyword_extractor: %s' % keyword_extractor_name
    )


def etl_keywords(
        keyword_extract_config: KeywordExtractConfig,
        full_file_location: str):
    """
    :param keyword_extract_config:
    :param full_file_location:
    :return:
    """

    keyword_extractor = get_keyword_extractor(keyword_extract_config)
    bq_query_processing = BqQuery(
        project_name=keyword_extract_config.gcp_project)
    downloaded_data = download_data(
        bq_query_processing,
        " ".join([keyword_extract_config.query_template,
                  keyword_extract_config.limit_return_count]),
        keyword_extract_config.gcp_project,
        keyword_extract_config.source_dataset,
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


def current_timestamp_as_string():
    """
    :return:
    """
    dtobj = datetime.datetime.now(timezone.utc)
    return dtobj.strftime("%Y-%m-%dT%H:%M:%SZ")


def download_data(
        bq_query_processing, query_template, gcp_project, source_dataset
) -> Iterable[dict]:
    """
    :param bq_query_processing:
    :param query_template:
    :param gcp_project:
    :param source_dataset:
    :return:
    """
    rows = bq_query_processing.simple_query(
        query_template, gcp_project, source_dataset
    )
    return rows


def add_timestamp(record_list, timestamp_field_name, timestamp_as_string):
    """
    :param record_list:
    :param timestamp_field_name:
    :param timestamp_as_string:
    :return:
    """
    for record in record_list:
        record[timestamp_field_name] = timestamp_as_string
        yield record


def write_to_file(json_list, full_temp_file_location):
    """
    :param json_list:
    :param full_temp_file_location:
    :return:
    """
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
