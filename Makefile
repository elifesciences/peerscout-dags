#!/usr/bin/make -f

DOCKER_COMPOSE_CI = docker-compose
DOCKER_COMPOSE_DEV = docker-compose -f docker-compose.yml -f docker-compose.dev.override.yml
DOCKER_COMPOSE = $(DOCKER_COMPOSE_DEV)

VENV = venv
PIP = $(VENV)/bin/pip
PYTHON = PYTHONPATH=dags $(VENV)/bin/python

NOT_SLOW_PYTEST_ARGS = -m 'not slow'

PYTEST_WATCH_SPACY_MODEL_MINIMAL = en_core_web_sm
PYTEST_WATCH_SPACY_MODEL_FULL = en_core_web_md

PEERSCOUT_DAGS_AIRFLOW_PORT = $(shell bash -c 'source .env && echo $$PEERSCOUT_DAGS_AIRFLOW_PORT')

AIRFLOW_DOCKER_COMPOSE = PEERSCOUT_DAGS_AIRFLOW_PORT="$(PEERSCOUT_DAGS_AIRFLOW_PORT)" \
	$(DOCKER_COMPOSE)


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

dev-nlp-model-download:
	$(PYTHON) -m spacy download en_core_web_lg
	$(PYTHON) -m spacy download en_core_web_md
	$(PYTHON) -m spacy download en_core_web_sm

dev-venv: venv-create dev-install dev-nlp-model-download


dev-flake8:
	$(PYTHON) -m flake8 peerscout dags tests

dev-pylint:
	$(PYTHON) -m pylint peerscout dags tests

dev-mypy:
	$(PYTHON) -m mypy --check-untyped-defs peerscout dags tests

dev-lint: dev-flake8 dev-pylint dev-mypy

dev-unittest:
	$(PYTHON) -m pytest -p no:cacheprovider $(ARGS) tests/unit_test

dev-dagtest:
	$(PYTHON) -m pytest -p no:cacheprovider $(ARGS) tests/dag_validation_test

dev-integration-test: dev-install
	(VENV)/bin/airflow upgradedb
	$(PYTHON) -m pytest -p no:cacheprovider $(ARGS) tests/integration_test

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


dev-test: dev-lint dev-unittest dev-dagtest


airflow-build:
	$(AIRFLOW_DOCKER_COMPOSE) build peerscout-dags

airflow-dev-build:
	$(AIRFLOW_DOCKER_COMPOSE) build peerscout-dags-dev


airflow-dev-shell:
	$(AIRFLOW_DOCKER_COMPOSE) run --rm peerscout-dags-dev bash


airflow-print-url:
	@echo "airflow url: http://localhost:$(PEERSCOUT_DAGS_AIRFLOW_PORT)"


airflow-scheduler-exec:
	$(AIRFLOW_DOCKER_COMPOSE) exec scheduler bash


airflow-logs:
	$(AIRFLOW_DOCKER_COMPOSE) logs -f scheduler webserver worker


airflow-start:
	$(AIRFLOW_DOCKER_COMPOSE) up worker webserver
	$(MAKE) airflow-print-url


airflow-stop:
	$(AIRFLOW_DOCKER_COMPOSE) down


build: airflow-build

build-dev: airflow-dev-build

clean:
	$(DOCKER_COMPOSE) down -v

airflow-db-migrate:
	$(DOCKER_COMPOSE) run --rm  webserver db migrate

airflow-initdb:
	$(DOCKER_COMPOSE) run --rm  webserver db init


end2end-test:
	$(MAKE) clean
	$(MAKE) airflow-db-migrate
	$(MAKE) airflow-initdb
	$(DOCKER_COMPOSE) run --rm  test-client
	$(MAKE) clean

ci-build-dev:
	$(MAKE) DOCKER_COMPOSE="$(DOCKER_COMPOSE_CI)" build-dev

ci-test-exclude-e2e: build-dev
	$(DOCKER_COMPOSE_CI) run --rm peerscout-dags-dev ./run_test.sh

ci-test-including-end2end: build-dev
	$(MAKE) DOCKER_COMPOSE="$(DOCKER_COMPOSE_CI)" end2end-test

ci-end2end-test-logs:
	$(DOCKER_COMPOSE_CI) exec worker bash -c \
		'cat logs/Extract_Keywords_From_Corpus/etl_keyword_extraction_task/*/*.log'

dev-env: airflow-start airflow-logs

ci-clean:
	$(DOCKER_COMPOSE_CI) down -v
