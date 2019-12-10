import re
from typing import List

from spacy.language import Language
from spacy.tokens import Doc, Span


DEFAULT_SPACY_LANGUAGE_MODEL_NAME = "en_core_web_lg"


class SpacyKeywordList:
    def __init__(self, language: Language, keyword_spans: List[Span]):
        self.language = language
        self.keyword_spans = keyword_spans

    @property
    def text_list(self) -> List[str]:
        return [span.text for span in self.keyword_spans]

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
