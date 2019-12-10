import pytest

from spacy.language import Language

from peerscout.keyword_extract.spacy_keyword import SpacyKeywordDocumentParser


@pytest.fixture(name="spacy_keyword_document_parser", scope="session")
def _spacy_keyword_document_parser(spacy_language_en: Language):
    return SpacyKeywordDocumentParser(spacy_language_en)


class TestSpacyKeywordDocumentParser:
    def test_should_extract_single_word_noun(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert (
            spacy_keyword_document_parser.parse_text('use technology')
            .compound_keywords
            .text_list
        ) == ['technology']

    def test_should_extract_single_noun_with_adjective(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert (
            spacy_keyword_document_parser.parse_text('use advanced technology')
            .compound_keywords
            .text_list
        ) == ['advanced technology']

    def test_should_normalize_text(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert (
            spacy_keyword_document_parser.parse_text(
                'use advanced \n\n technology'
            )
            .compound_keywords
            .text_list
        ) == ['advanced technology']

    def test_should_extract_individual_tokens(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert set(
            spacy_keyword_document_parser.parse_text('use advanced technology')
            .compound_keywords
            .with_individual_tokens
            .text_list
        ) == {'advanced technology', 'advanced', 'technology'}

    def test_should_exclude_pronouns(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert (
            spacy_keyword_document_parser.parse_text('we use technology')
            .compound_keywords
            .text_list
        ) == ['technology']

    def test_should_exclude_person_name(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert (
            spacy_keyword_document_parser.parse_text(
                'In collaboration with John Smith'
            )
            .compound_keywords
            .text_list
        ) == ['collaboration']

    def test_should_exclude_country_name(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert (
            spacy_keyword_document_parser.parse_text(
                'We research technology in the United Kingdom'
            )
            .compound_keywords
            .text_list
        ) == ['technology']

    def test_should_exclude_numbers(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert (
            spacy_keyword_document_parser.parse_text(
                r'technology that account for 123'
            )
            .compound_keywords
            .text_list
        ) == ['technology']

    def test_should_exclude_percentage(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert (
            spacy_keyword_document_parser.parse_text(
                r'technology that account for 95%'
            )
            .compound_keywords
            .text_list
        ) == ['technology']

    def test_should_exclude_greater_than_percentage(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert (
            spacy_keyword_document_parser.parse_text(
                r'technology that account for >95%'
            )
            .compound_keywords
            .text_list
        ) == ['technology']

    def test_should_convert_plural_to_singular_keyword(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert (
            spacy_keyword_document_parser.parse_text(
                'we investigate technologies'
            )
            .compound_keywords
            .normalized_text_list
        ) == ['technology']

    def test_should_normalize_keyword_spelling(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert (
            # need to use a word that is in the small spacy model
            spacy_keyword_document_parser.parse_text(
                'we investigate somethin'
            )
            .compound_keywords
            .normalized_text_list
        ) == ['something']
