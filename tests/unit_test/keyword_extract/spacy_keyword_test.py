import pytest

from spacy.language import Language

from peerscout.keyword_extract.spacy_keyword import (
    get_normalized_span_text,
    SpacyKeywordDocumentParser
)


@pytest.fixture(name="spacy_keyword_document_parser", scope="session")
def _spacy_keyword_document_parser(spacy_language_en: Language):
    return SpacyKeywordDocumentParser(spacy_language_en)


@pytest.fixture(name="spacy_keyword_document_parser_full", scope="session")
def _spacy_keyword_document_parser_full(spacy_language_en_full: Language):
    return SpacyKeywordDocumentParser(spacy_language_en_full)


class TestGetNormalizedSpanText:
    def test_should_convert_plural_to_singular(
            self, spacy_language_en: Language):
        assert get_normalized_span_text(spacy_language_en(
            "technologies"
        )) == 'technology'

    def test_should_normalize_remove_apostrophe(
            self, spacy_language_en: Language):
        assert get_normalized_span_text(spacy_language_en(
            "Parkinson's"
        )) == 'parkinson'

    def test_should_to_lower_case(
            self, spacy_language_en: Language):
        assert get_normalized_span_text(spacy_language_en(
            "fMRI"
        )) == 'fmri'


class TestSpacyKeywordDocumentParser:
    def test_should_extract_single_word_noun(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert (
            spacy_keyword_document_parser.parse_text('using technology')
            .compound_keywords
            .text_list
        ) == ['technology']

    def test_should_extract_single_noun_with_adjective(
            self, spacy_keyword_document_parser: SpacyKeywordDocumentParser):
        assert (
            spacy_keyword_document_parser.parse_text(
                'using advanced technology'
            )
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
            spacy_keyword_document_parser.parse_text(
                'using advanced technology'
            )
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

    @pytest.mark.slow
    def test_should_extract_conjunction_nouns_with_adjective_with_comma(
            self,
            spacy_keyword_document_parser_full: SpacyKeywordDocumentParser):
        # using "full" model,
        # the dependency tree is not complete using small model
        assert set(
            spacy_keyword_document_parser_full.parse_text(
                'we use advanced technique, advanced, and special technology'
            )
            .compound_keywords
            .text_list
        ) == {
            'advanced technique', 'advanced technology', 'special technology'
        }
