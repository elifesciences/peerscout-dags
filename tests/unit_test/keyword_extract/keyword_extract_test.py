from peerscout.keyword_extract.keyword_extract import (
    SimpleKeywordExtractor
)


class TestSimpleKeywordExtractor:
    def test_should_extract_individual_words(self):
        assert (
            SimpleKeywordExtractor().extract_keywords('the keywords')
            == ['the', 'keywords']
        )
