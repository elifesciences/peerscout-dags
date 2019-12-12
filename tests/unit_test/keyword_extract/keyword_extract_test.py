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
