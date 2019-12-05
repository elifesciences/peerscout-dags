import pytest

import spacy
from spacy.language import Language

from peerscout.keyword_extract.spacy_keyword import SpacyKeywordExtractor


@pytest.fixture(name="spacy_language_en", scope="session")
def _spacy_language_en():
    return spacy.load("en_core_web_sm")


@pytest.fixture(name="spacy_keyword_extractor", scope="session")
def _spacy_keyword_extractor(spacy_language_en: Language):
    return SpacyKeywordExtractor(spacy_language_en)


class TestSpacyKeywordExtractor:
    def test_should_extract_single_word_noun(
            self, spacy_keyword_extractor: SpacyKeywordExtractor):
        assert (
            spacy_keyword_extractor.parse_text('use technology')
            .compound_keywords
            .text_list
        ) == ['technology']

    def test_should_extract_single_noun_with_adjective(
            self, spacy_keyword_extractor: SpacyKeywordExtractor):
        assert (
            spacy_keyword_extractor.parse_text('use advanced technology')
            .compound_keywords
            .text_list
        ) == ['advanced technology']

    def test_should_normalize_text(
            self, spacy_keyword_extractor: SpacyKeywordExtractor):
        assert (
            spacy_keyword_extractor.parse_text('use advanced \n\n technology')
            .compound_keywords
            .text_list
        ) == ['advanced technology']

    def test_should_extract_individual_tokens(
            self, spacy_keyword_extractor: SpacyKeywordExtractor):
        assert set(
            spacy_keyword_extractor.parse_text('use advanced technology')
            .compound_keywords
            .with_individual_tokens
            .text_list
        ) == {'advanced technology', 'advanced', 'technology'}
