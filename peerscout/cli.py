import logging
import os
from typing import Optional

import yaml

from peerscout.keyword_extract.keyword_extract import current_timestamp_as_string, etl_keywords
from peerscout.keyword_extract.keyword_extract_config import (
    KeywordExtractConfig,
    MultiKeywordExtractConfig
)
from peerscout.utils.s3_data_service import get_stored_state


LOGGER = logging.getLogger(__name__)


DEPLOYMENT_ENV = 'DEPLOYMENT_ENV'


DEFAULT_DEPLOYMENT_ENV = 'ci'


EXTRACT_KEYWORDS_CONFIG_FILE_PATH_ENV_NAME = 'EXTRACT_KEYWORDS_FILE_PATH'


SPACY_LANGUAGE_MODEL_ENV_NAME = 'SPACY_LANGUAGE_MODEL'


def get_yaml_file_as_dict(file_location: str) -> dict:
    with open(file_location, 'r', encoding='UTF-8') as yaml_file:
        return yaml.safe_load(yaml_file)


def get_deployment_env() -> str:
    return os.getenv(DEPLOYMENT_ENV, DEFAULT_DEPLOYMENT_ENV)


def get_spacy_language_model_override() -> Optional[str]:
    return os.getenv(SPACY_LANGUAGE_MODEL_ENV_NAME)


def get_data_config() -> dict:
    conf_file_path = os.environ[EXTRACT_KEYWORDS_CONFIG_FILE_PATH_ENV_NAME]
    return get_yaml_file_as_dict(
        conf_file_path
    )


def main():
    multi_keyword_extract_conf_dict = get_data_config()
    LOGGER.info('config: %r', multi_keyword_extract_conf_dict)
    dep_env = get_deployment_env()
    LOGGER.info('deployment env: %r', dep_env)
    multi_keyword_extract_conf = MultiKeywordExtractConfig(
        multi_keyword_extract_conf_dict,
        dep_env
    )
    LOGGER.info('multi_keyword_extract_conf: %r', multi_keyword_extract_conf)
    LOGGER.info(
        'state file path: s3://%s/%s',
        multi_keyword_extract_conf.state_file_bucket_name,
        multi_keyword_extract_conf.state_file_object_name
    )
    state_dict = get_stored_state(
        multi_keyword_extract_conf.state_file_bucket_name,
        multi_keyword_extract_conf.state_file_object_name
    )
    LOGGER.info('state_dict: %r', state_dict)
    timestamp_as_string = current_timestamp_as_string()
    LOGGER.info('timestamp_as_string: %r', timestamp_as_string)
    spacy_language_model_override = get_spacy_language_model_override()
    LOGGER.info('spacy_language_model_override: %r', spacy_language_model_override)
    for extract_conf_dict in multi_keyword_extract_conf.keyword_extract_config:
        keyword_extract_config = KeywordExtractConfig(
            extract_conf_dict,
            gcp_project=multi_keyword_extract_conf.gcp_project,
            import_timestamp_field_name=(
                multi_keyword_extract_conf.import_timestamp_field_name
            ),
            spacy_language_model=spacy_language_model_override
        )
        LOGGER.info('keyword_extract_config: %r', keyword_extract_config)
        etl_keywords(
            keyword_extract_config=keyword_extract_config,
            timestamp_as_string=timestamp_as_string,
            state_s3_bucket=multi_keyword_extract_conf.state_file_bucket_name,
            state_s3_object=multi_keyword_extract_conf.state_file_object_name,
            data_pipelines_state=state_dict
        )


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
