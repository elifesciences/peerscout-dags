import re
from typing import List

from spacy.language import Language
from spacy.tokens import Doc, Span, Token


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
    return span[:-1].text_with_ws + get_normalized_token_text(span[-1])


class SpacyKeywordList:
    def __init__(self, language: Language, keyword_spans: List[Span]):
        self.language = language
        self.keyword_spans = keyword_spans

    @property
    def text_list(self) -> List[str]:
        return [span.text for span in self.keyword_spans]

    @property
    def normalized_text_list(self) -> List[str]:
        return [get_normalized_span_text(span) for span in self.keyword_spans]

    @property
    def with_individual_tokens(self) -> 'SpacyKeywordList':
        keyword_spans = self.keyword_spans.copy()
        for keyword_span in keyword_spans:
            individual_keywords = keyword_span.text.split(' ')
            if len(individual_keywords) > 1:
                for individual_keyword in individual_keywords:
                    keyword_spans.append(self.language(individual_keyword))
        return SpacyKeywordList(self.language, keyword_spans)


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
            for span in self.doc.noun_chunks
            if self.should_use_span_as_keyword(span)
        ]

    @property
    def compound_keywords(self) -> SpacyKeywordList:
        return SpacyKeywordList(self.language, self.get_compound_keyword_spans())


class SpacyKeywordDocumentParser:
    def __init__(self, language: Language):
        self.language = language

    def normalize_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def parse_text(self, text: str) -> SpacyKeywordDocument:
        return SpacyKeywordDocument(
            self.language,
            self.language(self.normalize_text(text))
        )
