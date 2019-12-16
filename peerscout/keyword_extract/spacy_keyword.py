import re
import logging
from typing import Iterable, List

from spacy.language import Language
from spacy.tokens import Doc, Span, Token


LOGGER = logging.getLogger(__name__)


DEFAULT_SPACY_LANGUAGE_MODEL_NAME = "en_core_web_lg"


def get_token_lemma(token: Token) -> str:
    lemma = token.lemma_
    if lemma.startswith('-'):
        return token.text
    return lemma


def get_span_lemma(span: Span) -> str:
    return span[:-1].text_with_ws + get_token_lemma(span[-1])


def get_normalized_token_text(token: Token) -> str:
    if token.norm_ != token.text:
        return token.norm_
    return get_token_lemma(token)


def get_span_without_apostrophe(span: Span) -> Span:
    if span[-1].tag_ == 'POS':
        span = span[:-1]
    return span


def get_normalized_span_text(span: Span) -> str:
    span = get_span_without_apostrophe(span)
    return (
        span[:-1].text_with_ws + get_normalized_token_text(span[-1])
    ).lower()


def is_conjunction_token(token: Token) -> bool:
    return token.pos_ == 'CCONJ'


def get_text_list(spans: List[Span]) -> List[str]:
    return [span.text for span in spans]


def join_spans(spans: List[Span], language: Language) -> Span:
    # there doesn't seem to be an easy way to create a span
    # from a list of tokens. parsing the text for now.
    # (In the future look into doc.retokenize)
    joined_text = ' '.join([span.text for span in spans])
    LOGGER.debug('joined_text: %s', joined_text)
    return language(joined_text)


def get_noun_tokens(doc: Doc) -> List[Token]:
    return [token for token in doc if token.pos_ == 'NOUN']


def get_noun_chunk_for_noun_token(noun_token: Token) -> Span:
    index = noun_token.i
    return noun_token.doc[index:index + 1]


def get_noun_chunks(doc: Doc) -> List[Span]:
    # prefer using spacy's noun chunks, add noun chunks not covered by spacy
    noun_chunks = list(doc.noun_chunks)
    included_noun_tokens = {token for span in noun_chunks for token in span}
    noun_tokens_not_already_in_noun_chunks = [
        noun_token
        for noun_token in get_noun_tokens(doc)
        if noun_token not in included_noun_tokens
    ]
    LOGGER.debug(
        'included_noun_tokens: %s',
        included_noun_tokens
    )
    LOGGER.debug(
        'noun_tokens_not_already_in_noun_chunks: %s',
        noun_tokens_not_already_in_noun_chunks
    )
    for noun_token in noun_tokens_not_already_in_noun_chunks:
        noun_chunks.append(get_noun_chunk_for_noun_token(noun_token))
    return noun_chunks


def iter_split_noun_chunk_conjunctions(
        noun_chunk: Span,
        language: Language) -> Iterable[Span]:
    previous_start = 0
    previous_end = 0
    for index, token in enumerate(noun_chunk):
        if not is_conjunction_token(token):
            previous_end = index + 1
            continue
        LOGGER.debug(
            'conjunction token "%s", previous token: %d..%d',
            token, previous_start, previous_end
        )
        if previous_end > previous_start:
            yield join_spans([
                noun_chunk[previous_start:previous_end],
                noun_chunk[-1:]
            ], language=language)
            previous_start = index + 1
            previous_end = previous_start
    if previous_end > previous_start:
        remaining_span = noun_chunk[previous_start:previous_end]
        LOGGER.debug('remaining_span: %s', remaining_span)
        yield remaining_span


def get_conjuction_noun_chunks(
        doc: Doc,
        language: Language) -> List[Span]:
    noun_chunks = get_noun_chunks(doc)
    for noun_chunk in list(noun_chunks):
        last_noun_token = noun_chunk[-1]
        LOGGER.debug(
            'last_noun_token: %s (conjuncts: %s)',
            last_noun_token, last_noun_token.conjuncts
        )
        for conjunction_token in last_noun_token.conjuncts:
            conjunction_children = list(conjunction_token.children)
            if last_noun_token not in conjunction_children:
                LOGGER.debug(
                    ' '.join([
                        'last_noun_token not in children',
                        '("%s" ~ children %s of "%s")',
                    ]),
                    last_noun_token,
                    conjunction_children,
                    conjunction_token
                )
                continue
            if conjunction_token.pos_ != 'ADJ':
                LOGGER.debug(
                    'conjunction_token not ADJ: "%s" (pos: %s)',
                    conjunction_token, conjunction_token.pos_
                )
                continue
            conjunction_span = join_spans([
                conjunction_token, noun_chunk[-1:]
            ], language=language)
            LOGGER.debug('adding conjunction_span: %s', conjunction_span)
            noun_chunks += [conjunction_span]
    return [
        split_noun_chunk
        for noun_chunk in noun_chunks
        for split_noun_chunk in iter_split_noun_chunk_conjunctions(
            noun_chunk,
            language=language
        )
    ]


def iter_individual_keyword_spans(
        keyword_span: Span,
        language: Language) -> Iterable[Span]:
    individual_keywords = keyword_span.text.split(' ')
    if len(individual_keywords) > 1:
        for individual_keyword in individual_keywords:
            yield language(individual_keyword)


def iter_shorter_keyword_spans(
        keyword_span: Span,
        language: Language) -> Iterable[Span]:
    individual_keywords = keyword_span.text.split(' ')
    for start in range(1, len(individual_keywords) - 1):
        yield language(' '.join(individual_keywords[start:]))


def lstrip_stop_words_and_punc(span: Span) -> Span:
    for index in reversed(range(0, len(span))):
        token = span[index]
        if token.pos_ == 'PART':
            continue
        if token.is_stop or token.pos_ == 'PUNCT':
            LOGGER.debug(
                'stripping span at token "%s" (pos: %s, stop: %s)',
                token, token.pos_, token.is_stop
            )
            return span[index + 1:]
    return span


def normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


class SpacyKeywordList:
    def __init__(self, language: Language, keyword_spans: List[Span]):
        self.language = language
        self.keyword_spans = keyword_spans

    @property
    def text_list(self) -> List[str]:
        return get_text_list(self.keyword_spans)

    @property
    def normalized_text_list(self) -> List[str]:
        return [get_normalized_span_text(span) for span in self.keyword_spans]

    def with_keyword_spans(
            self, keyword_spans: List[Span]) -> 'SpacyKeywordList':
        return SpacyKeywordList(self.language, keyword_spans)

    def with_additional_keyword_spans(
            self, additional_keyword_spans: List[Span]) -> 'SpacyKeywordList':
        return self.with_keyword_spans(
            self.keyword_spans + additional_keyword_spans
        )

    @property
    def with_lstripped_stop_words_and_punct(self) -> 'SpacyKeywordList':
        return self.with_keyword_spans(
            list(map(lstrip_stop_words_and_punc, self.keyword_spans))
        )

    @property
    def with_individual_tokens(self) -> 'SpacyKeywordList':
        return self.with_additional_keyword_spans([
            individual_keyword_span
            for keyword_span in self.keyword_spans
            for individual_keyword_span in iter_individual_keyword_spans(
                keyword_span,
                language=self.language
            )
        ])

    @property
    def with_shorter_keywords(self) -> 'SpacyKeywordList':
        return self.with_additional_keyword_spans([
            shorter_keyword_span
            for keyword_span in self.keyword_spans
            for shorter_keyword_span in iter_shorter_keyword_spans(
                keyword_span,
                language=self.language
            )
        ])


class SpacyKeywordDocument:
    def __init__(self, language: Language, doc: Doc):
        self.language = language
        self.doc = doc

    def should_use_span_as_keyword(self, span: Span) -> bool:
        last_token = span[-1]
        return (
            last_token.ent_type_ not in {'PERSON', 'GPE', 'PERCENT'}
            and last_token.pos_ not in {'PRON'}
            and not last_token.is_stop
        )

    def get_compound_keyword_spans(self) -> List[Span]:
        return [
            span
            for span in get_conjuction_noun_chunks(
                self.doc, language=self.language
            )
            if self.should_use_span_as_keyword(span)
        ]

    @property
    def compound_keywords(self) -> SpacyKeywordList:
        return SpacyKeywordList(
            self.language, self.get_compound_keyword_spans()
        )


class SpacyKeywordDocumentParser:
    def __init__(self, language: Language):
        self.language = language

    def normalize_text_list(self, text_list: Iterable[str]) -> Iterable[str]:
        return (normalize_text(text) for text in text_list)

    def parse_text(self, text: str) -> SpacyKeywordDocument:
        return list(self.iter_parse_text_list([text]))[0]

    def iter_parse_text_list(
            self, text_list: Iterable[str]) -> Iterable[SpacyKeywordDocument]:
        return (
            SpacyKeywordDocument(
                self.language,
                doc
            )
            for doc in self.language.pipe(
                self.normalize_text_list(text_list)
            )
        )
