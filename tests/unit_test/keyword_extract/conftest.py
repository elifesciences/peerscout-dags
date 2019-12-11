import logging
import os
from typing import Dict

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


def _get_or_load_spacy_model(
        language_model_name: str,
        spacy_model_cache: Dict[str, Language]) -> Language:
    language_model = spacy_model_cache.get(language_model_name)
    if language_model is None:
        language_model = _load_spacy_model(language_model_name)
        spacy_model_cache[language_model_name] = language_model
    return language_model


@pytest.fixture(name="spacy_model_cache", scope="session")
def _spacy_model_cache() -> Dict[str, Language]:
    return {}


@pytest.fixture(name="spacy_language_en", scope="session")
def _spacy_language_en(spacy_model_cache: Dict[str, Language]) -> Language:
    return _get_or_load_spacy_model(os.environ.get(
        EnvVars.SPACY_LANGUAGE_EN_MINIMAL,
        DEFAULT_SPACY_LANGUAGE_MODEL_NAME
    ), spacy_model_cache=spacy_model_cache)


@pytest.fixture(name="spacy_language_en_full", scope="session")
def _spacy_language_en_full(spacy_model_cache: Dict[str, Language]) -> Language:
    return _get_or_load_spacy_model(os.environ.get(
        EnvVars.SPACY_LANGUAGE_EN_FULL,
        DEFAULT_SPACY_LANGUAGE_MODEL_NAME
    ), spacy_model_cache=spacy_model_cache)
