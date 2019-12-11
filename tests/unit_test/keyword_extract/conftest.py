import logging
import os

import pytest

import spacy
from spacy.language import Language

from peerscout.keyword_extract.spacy_keyword import (
    DEFAULT_SPACY_LANGUAGE_MODEL_NAME
)


LOGGER = logging.getLogger(__name__)


class EnvVars:
    SPACY_LANGUAGE_EN_MINIMAL = "SPACY_LANGUAGE_EN_MINIMAL"
    SPACY_LANGUAGE_EN_FULL = "SPACY_LANGUAGE_EN_FULL"


def _load_spacy_model(language_model_name: str) -> Language:
    LOGGER.debug("loading spacy model: %s", language_model_name)
    return spacy.load(language_model_name)


@pytest.fixture(name="spacy_language_en", scope="session")
def _spacy_language_en() -> Language:
    return _load_spacy_model(os.environ.get(
        EnvVars.SPACY_LANGUAGE_EN_MINIMAL,
        DEFAULT_SPACY_LANGUAGE_MODEL_NAME
    ))


@pytest.fixture(name="spacy_language_en_full", scope="session")
def _spacy_language_en_full() -> Language:
    return _load_spacy_model(os.environ.get(
        EnvVars.SPACY_LANGUAGE_EN_FULL,
        DEFAULT_SPACY_LANGUAGE_MODEL_NAME
    ))
