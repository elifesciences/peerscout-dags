import pytest

from spacy.language import Language

from peerscout.keyword_extract.spacy_keyword import (
    get_span_without_apostrophe,
    get_normalized_span_text,
    is_conjunction_token,
    join_spans,
    iter_split_noun_chunk_conjunctions,
    get_conjuction_noun_chunks,
    iter_individual_keyword_spans,
    iter_shorter_keyword_spans,
    SpacyKeywordDocumentParser
)


@pytest.fixture(name="spacy_keyword_document_parser", scope="session")
def _spacy_keyword_document_parser(spacy_language_en: Language):
    return SpacyKeywordDocumentParser(spacy_language_en)


@pytest.fixture(name="spacy_keyword_document_parser_full", scope="session")
def _spacy_keyword_document_parser_full(spacy_language_en_full: Language):
    return SpacyKeywordDocumentParser(spacy_language_en_full)


class TestGetSpanWithoutApostrophe:
    def test_should_remove_apostrophe(
            self, spacy_language_en: Language):
        assert get_span_without_apostrophe(spacy_language_en(
            "Johnson's"
        )).text == "Johnson"


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

    def test_should_convert_single_token_to_lower_case(
            self, spacy_language_en: Language):
        assert get_normalized_span_text(spacy_language_en(
            "fMRI"
        )) == 'fmri'

    def test_should_convert_multiple_token_span_to_lower_case(
            self, spacy_language_en: Language):
        assert get_normalized_span_text(spacy_language_en(
            "Advanced Technology"
        )) == 'advanced technology'


class TestIsConjunctionToken:
    def test_should_return_true_for_and_token_only(
            self, spacy_language_en: Language):
        assert [
            is_conjunction_token(token)
            for token in spacy_language_en('this and that')
        ] == [False, True, False]


class TestJoinSpans:
    def test_should_join_two_spans(
            self, spacy_language_en: Language):
        assert join_spans(
            [
                spacy_language_en('the joined'),
                spacy_language_en('span')
            ],
            language=spacy_language_en
        ).text == 'the joined span'


class TestIterSplitNounChunkConjunctions:
    def test_should_not_split_noun_chunk_without_conjunctions(
            self, spacy_language_en: Language):
        assert [span.text for span in iter_split_noun_chunk_conjunctions(
            spacy_language_en('advanced technology'),
            language=spacy_language_en
        )] == ['advanced technology']

    def test_should_split_and_join_noun_chunk_on_conjunction(
            self, spacy_language_en: Language):
        assert [span.text for span in iter_split_noun_chunk_conjunctions(
            spacy_language_en('advanced and special technology'),
            language=spacy_language_en
        )] == ['advanced technology', 'special technology']


class TestGetConjuctionNounChunks:
    def test_should_not_split_noun_chunk_without_conjunctions(
            self, spacy_language_en: Language):
        assert [span.text for span in get_conjuction_noun_chunks(
            spacy_language_en('advanced technology'),
            language=spacy_language_en
        )] == ['advanced technology']

    def test_should_split_and_join_noun_chunk_on_conjunction_without_comma(
            self, spacy_language_en: Language):
        assert [span.text for span in get_conjuction_noun_chunks(
            spacy_language_en('advanced and special technology'),
            language=spacy_language_en
        )] == ['advanced technology', 'special technology']

    def test_should_split_and_join_noun_chunk_on_conjunction_with_comma(
            self, spacy_language_en: Language):
        assert {span.text for span in get_conjuction_noun_chunks(
            spacy_language_en('advanced, and special technology'),
            language=spacy_language_en
        )} == {'advanced technology', 'special technology'}


class TestIterIndividualKeywordSpans:
    def test_should_return_no_results_if_keyword_is_not_compound(
            self, spacy_language_en: Language):
        assert [span.text for span in iter_individual_keyword_spans(
            spacy_language_en('technology'),
            language=spacy_language_en
        )] == []

    def test_should_return_individual_words_from_compound_keyword(
            self, spacy_language_en: Language):
        assert [span.text for span in iter_individual_keyword_spans(
            spacy_language_en('advanced technology'),
            language=spacy_language_en
        )] == ['advanced', 'technology']

    def test_should_only_return_individual_words_from_larger_compound_keyword(
            self, spacy_language_en: Language):
        assert [span.text for span in iter_individual_keyword_spans(
            spacy_language_en('very advanced technology'),
            language=spacy_language_en
        )] == ['very', 'advanced', 'technology']


class TestIterShorterKeywordSpans:
    def test_should_return_no_results_if_keyword_is_not_compound(
            self, spacy_language_en: Language):
        assert [span.text for span in iter_shorter_keyword_spans(
            spacy_language_en('technology'),
            language=spacy_language_en
        )] == []

    def test_should_return_no_results_for_two_word_keyword(
            self, spacy_language_en: Language):
        assert [span.text for span in iter_shorter_keyword_spans(
            spacy_language_en('advanced technology'),
            language=spacy_language_en
        )] == []

    def test_should_return_last_two_words_for_three_word_keyword(
            self, spacy_language_en: Language):
        assert [span.text for span in iter_shorter_keyword_spans(
            spacy_language_en('very advanced technology'),
            language=spacy_language_en
        )] == ['advanced technology']

    def test_should_return_last_three_and_two_words_for_four_word_keyword(
            self, spacy_language_en: Language):
        assert [span.text for span in iter_shorter_keyword_spans(
            spacy_language_en('very extra advanced technology'),
            language=spacy_language_en
        )] == ['extra advanced technology', 'advanced technology']


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

    @pytest.mark.slow
    def test_should_extract_conjunction_nouns_with_adjective_without_comma(
            self,
            spacy_keyword_document_parser_full: SpacyKeywordDocumentParser):
        # using "full" model,
        # the dependency tree is not complete using small model
        assert set(
            spacy_keyword_document_parser_full.parse_text(
                'we use advanced technique, advanced and special technology'
            )
            .compound_keywords
            .text_list
        ) == {
            'advanced technique', 'advanced technology', 'special technology'
        }

    @pytest.mark.slow
    def test_should_not_combine_two_separate_nouns_with_conjunction(
            self,
            spacy_keyword_document_parser_full: SpacyKeywordDocumentParser):
        # using "full" model,
        # the dependency tree is not complete using small model
        assert set(
            spacy_keyword_document_parser_full.parse_text(
                'we use technique and technology'
            )
            .compound_keywords
            .text_list
        ) == {
            'technique', 'technology'
        }
