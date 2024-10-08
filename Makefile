#!/usr/bin/make -f

DOCKER_COMPOSE_CI = docker-compose
DOCKER_COMPOSE_DEV = docker-compose -f docker-compose.yml -f docker-compose.dev.override.yml
DOCKER_COMPOSE = $(DOCKER_COMPOSE_DEV)

VENV = venv
PIP = $(VENV)/bin/pip
PYTHON = $(VENV)/bin/python

NOT_SLOW_PYTEST_ARGS = -m 'not slow'

PYTEST_WATCH_SPACY_MODEL_MINIMAL = en_core_web_sm
PYTEST_WATCH_SPACY_MODEL_FULL = en_core_web_md


venv-clean:
	@if [ -d "$(VENV)" ]; then \
		rm -rf "$(VENV)"; \
	fi

venv-create:
	python3 -m venv $(VENV)

venv-activate:
	chmod +x venv/bin/activate
	bash -c "venv/bin/activate"

dev-install:
	$(PIP) install --disable-pip-version-check -r requirements.build.txt
	$(PIP) install --disable-pip-version-check -r requirements.spacy.txt
	SLUGIFY_USES_TEXT_UNIDECODE=yes \
	$(PIP) install --disable-pip-version-check -r requirements.txt
	$(PIP) install --disable-pip-version-check -r requirements.dev.txt
	$(PIP) install --disable-pip-version-check -e . --no-deps


dev-nlp-model-download-small:
	$(PYTHON) -m spacy download en_core_web_sm


dev-nlp-model-download:
	$(PYTHON) -m spacy download en_core_web_lg
	$(PYTHON) -m spacy download en_core_web_md
	$(PYTHON) -m spacy download en_core_web_sm

dev-venv: venv-create dev-install dev-nlp-model-download


dev-flake8:
	$(PYTHON) -m flake8 peerscout tests

dev-pylint:
	$(PYTHON) -m pylint peerscout tests

dev-mypy:
	$(PYTHON) -m mypy --check-untyped-defs peerscout tests

dev-lint: dev-flake8 dev-pylint dev-mypy

dev-unittest:
	$(PYTHON) -m pytest -p no:cacheprovider $(ARGS) tests/unit_test

dev-watch:
	SPACY_LANGUAGE_EN_MINIMAL=$(PYTEST_WATCH_SPACY_MODEL_MINIMAL) \
	SPACY_LANGUAGE_EN_FULL=$(PYTEST_WATCH_SPACY_MODEL_FULL) \
	$(PYTHON) -m pytest_watch -- -p no:cacheprovider \
		$(ARGS) $(NOT_SLOW_PYTEST_ARGS) tests/unit_test

dev-watch-slow:
	# using full model as "minimal" since we'll need to load it anyway
	# (and share it for the whole session)
	SPACY_LANGUAGE_EN_MINIMAL=$(PYTEST_WATCH_SPACY_MODEL_FULL) \
	SPACY_LANGUAGE_EN_FULL=$(PYTEST_WATCH_SPACY_MODEL_FULL) \
	$(PYTHON) -m pytest_watch -- -p no:cacheprovider \
		$(ARGS) tests/unit_test


dev-test: dev-lint dev-unittest


dev-data-hub-pipelines-run-keyword-extraction:
	EXTRACT_KEYWORDS_FILE_PATH=dev-config/peerscout-keyword-extraction-data-pipeline-editor-provided-keywords.config.yaml \
	$(PYTHON) -m peerscout.cli


build:
	$(DOCKER_COMPOSE) build peerscout-dags

build-dev:
	$(DOCKER_COMPOSE) build peerscout-dags-dev

shell-dev:
	$(DOCKER_COMPOSE) run --rm peerscout-dags-dev bash

clean:
	$(DOCKER_COMPOSE) down -v


data-hub-pipelines-run-keyword-extraction:
	$(DOCKER_COMPOSE) run --rm \
		data-hub-pipelines \
		python -m peerscout.cli


end2end-test:
	$(MAKE) clean
	$(DOCKER_COMPOSE) run --rm  test-client
	$(MAKE) clean

ci-build-main-image:
	$(MAKE) DOCKER_COMPOSE="$(DOCKER_COMPOSE_CI)" \
		build

ci-build-dev:
	$(MAKE) DOCKER_COMPOSE="$(DOCKER_COMPOSE_CI)" build-dev

ci-test-exclude-e2e: build-dev
	$(DOCKER_COMPOSE_CI) run --rm peerscout-dags-dev ./run_test.sh

ci-test-including-end2end: build-dev
	$(MAKE) DOCKER_COMPOSE="$(DOCKER_COMPOSE_CI)" end2end-test

ci-end2end-test-logs:
	$(DOCKER_COMPOSE_CI) exec worker bash -c \
		'cat logs/Extract_Keywords_From_Corpus/etl_keyword_extraction_task/*/*.log'

ci-clean:
	$(DOCKER_COMPOSE_CI) down -v


retag-push-image:
	docker tag  $(EXISTING_IMAGE_REPO):$(EXISTING_IMAGE_TAG) $(IMAGE_REPO):$(IMAGE_TAG)
	docker push  $(IMAGE_REPO):$(IMAGE_TAG)
