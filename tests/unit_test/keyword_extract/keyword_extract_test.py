from spacy.language import Language

from peerscout.keyword_extract.keyword_extract import (
    to_unique_keywords,
    SimpleKeywordExtractor,
    SpacyKeywordExtractor,
    add_extracted_keywords
)


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
