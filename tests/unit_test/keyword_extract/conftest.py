import pytest

import spacy
from spacy.language import Language


@pytest.fixture(name="spacy_language_en", scope="session")
def _spacy_language_en() -> Language:
    return spacy.load("en_core_web_sm")
