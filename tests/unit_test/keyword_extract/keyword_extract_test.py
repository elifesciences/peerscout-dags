from unittest.mock import patch, MagicMock

import pytest

from spacy.language import Language

import peerscout.keyword_extract.keyword_extract as keyword_extract_module
from peerscout.keyword_extract.keyword_extract import (
    to_unique_keywords,
    SimpleKeywordExtractor,
    SpacyKeywordExtractor,
    parse_keyword_list,
    add_extracted_keywords
)


@pytest.fixture(name="spacy_keyword_document_parser_class_mock")
def _spacy_keyword_document_parser_class_mock():
    with patch.object(
            keyword_extract_module, "SpacyKeywordDocumentParser") as mock:
        yield mock


@pytest.fixture(name="spacy_keyword_document_parser_mock")
def _spacy_keyword_document_parser_mock(
        spacy_keyword_document_parser_class_mock: MagicMock):
    return spacy_keyword_document_parser_class_mock.return_value


class TestToUniqueKeywords:
    def test_should_remove_duplicates_from_keywords(self):
        assert (
            to_unique_keywords(['keyword', 'keyword'])
            == ['keyword']
        )

    def test_should_add_additional_keywords(self):
        assert (
            to_unique_keywords(
                ['keyword'],
                additional_keywords=['other']
            ) == ['keyword', 'other']
        )

    def test_should_remove_duplicates_from_additional_keywords(self):
        assert (
            to_unique_keywords(
                ['keyword', 'keyword'],
                additional_keywords=['keyword', 'keyword']
            )
            == ['keyword']
        )


class TestSimpleKeywordExtractor:
    def test_should_extract_individual_words(self):
        assert (
            SimpleKeywordExtractor().extract_keywords('the keywords')
            == ['the', 'keywords']
        )

    def test_should_extract_individual_words_without_duplicates(self):
        assert (
            SimpleKeywordExtractor().extract_unique_keywords('keyword keyword')
            == ['keyword']
        )

    def test_should_add_additional_keywords(self):
        assert (
            SimpleKeywordExtractor().extract_unique_keywords(
                'keyword',
                additional_keywords=['other']
            ) == ['keyword', 'other']
        )

    def test_should_remove_duplicates_from_additional_keywords(self):
        assert (
            SimpleKeywordExtractor().extract_unique_keywords(
                'keyword keyword',
                additional_keywords=['keyword', 'keyword']
            ) == ['keyword']
        )


class TestSpacyKeywordExtractor:
    def test_should_extract_noun(self, spacy_language_en: Language):
        assert (
            SpacyKeywordExtractor(
                language=spacy_language_en
            ).extract_keywords('using keyword')
            == ['keyword']
        )

    def test_should_extract_individual_words_without_duplicates(
            self, spacy_language_en: Language):
        assert (
            SpacyKeywordExtractor(
                language=spacy_language_en
            ).extract_unique_keywords('using keyword and keyword')
            == ['keyword']
        )

    def test_should_call_iter_parse_text_list(
            self, spacy_language_en: Language,
            spacy_keyword_document_parser_mock: MagicMock):
        list(SpacyKeywordExtractor(
            language=spacy_language_en
        ).iter_extract_keywords(['using keyword', 'other keyword']))
        spacy_keyword_document_parser_mock.iter_parse_text_list.assert_called()


class TestParseKeywordList:
    def test_should_return_empty_list_if_keywords_str_is_none(self):
        assert parse_keyword_list("") == []

    def test_should_return_empty_list_if_keywords_str_is_empty(self):
        assert parse_keyword_list('') == []

    def test_should_return_empty_list_if_keywords_str_is_blank(self):
        assert parse_keyword_list(' ') == []

    def test_should_return_keywords_split_by_separator(self):
        assert (
            parse_keyword_list('keyword1,keyword2')
            == ['keyword1', 'keyword2']
        )

    def test_should_strip_blank_around_keywords(self):
        assert (
            parse_keyword_list(' keyword1 , keyword2 ')
            == ['keyword1', 'keyword2']
        )


class TestAddExtractedKeywords:
    def test_should_extract_keywords_with_existing_keywords(self):
        records = [{'text': 'the keywords', 'existing_keywords': 'existing'}]
        records_with_keywords = list(add_extracted_keywords(
            records,
            text_field='text',
            existing_keyword_field='existing_keywords',
            extracted_keyword_field_name='extracted_keywords',
            keyword_extractor=SimpleKeywordExtractor()
        ))
        assert set(records_with_keywords[0]['extracted_keywords']) == {
            'the', 'keywords', 'existing'
        }

    def test_should_extract_keywords_without_existing_keywords(self):
        records = [{'text': 'the keywords'}]
        records_with_keywords = list(add_extracted_keywords(
            records,
            text_field='text',
            existing_keyword_field='existing_keywords',
            extracted_keyword_field_name='extracted_keywords',
            keyword_extractor=SimpleKeywordExtractor()
        ))
        assert set(records_with_keywords[0]['extracted_keywords']) == {
            'the', 'keywords'
        }
