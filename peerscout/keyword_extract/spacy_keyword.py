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

    @property
    def compound_keywords(self) -> SpacyKeywordList:
        return SpacyKeywordList(self.language, list(self.doc.noun_chunks))


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
