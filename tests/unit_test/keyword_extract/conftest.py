import pytest

import spacy
from spacy.language import Language

from peerscout.keyword_extract.spacy_keyword import (
    DEFAULT_SPACY_LANGUAGE_MODEL_NAME
)


@pytest.fixture(name="spacy_language_en", scope="session")
def _spacy_language_en() -> Language:
    return spacy.load("en_core_web_sm")


@pytest.fixture(name="spacy_language_en_full", scope="session")
def _spacy_language_en_full() -> Language:
    return spacy.load(DEFAULT_SPACY_LANGUAGE_MODEL_NAME)
