from spacy.language import Language

from peerscout.keyword_extract.keyword_extract import (
    SimpleKeywordExtractor,
    SpacyKeywordExtractor
)


class TestSimpleKeywordExtractor:
    def test_should_extract_individual_words(self):
        assert (
            SimpleKeywordExtractor().extract_keywords('the keywords')
            == ['the', 'keywords']
        )


class TestSpacyKeywordExtractor:
    def test_should_extract_noun(self, spacy_language_en: Language):
        assert (
            SpacyKeywordExtractor(
                language=spacy_language_en
            ).extract_keywords('use keyword')
            == ['keyword']
        )
