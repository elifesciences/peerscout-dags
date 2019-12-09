"""
utils for doing the heavy lifting job of extracting keywords
"""

import json
import re
from typing import Iterable, List
import datetime
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


class KeywordExtractor(ABC):
    @abstractmethod
    def extract_keywords(self, text: str) -> List[str]:
        pass

    def extract_unique_keywords(self, text: str) -> List[str]:
        return sorted(set(self.extract_keywords(text)))


class SimpleKeywordExtractor(KeywordExtractor):
    def extract_keywords(self, text: str) -> List[str]:
        return simple_regex_keyword_extraction(text)


class SpacyKeywordExtractor(KeywordExtractor):
    def __init__(self, language: Language):
        self.language = language

    def extract_keywords(self, text: str) -> List[str]:
        return (
            SpacyKeywordDocumentParser(self.language)
            .parse_text(text)
            .compound_keywords
            .with_individual_tokens
            .text_list
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


def add_extracted_keywords(
        record_list,
        text_field,
        existing_keyword_field,
        keyword_extractor: KeywordExtractor,
        existing_keyword_split_pattern=",",
        extracted_keyword_field_name: str = "extracted_keywords",
):
    """
    :param record_list:
    :param text_field:
    :param existing_keyword_field:
    :param existing_keyword_split_pattern:
    :param extracted_keyword_field_name:
    :return:
    """
    for record in record_list:
        new_keywords = keyword_extractor.extract_unique_keywords(
            record.get(text_field, "")
        )
        new_keywords.extend(
            record.get(existing_keyword_field, "").split(
                existing_keyword_split_pattern
            )
        )
        record[extracted_keyword_field_name] = new_keywords
        yield record


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
