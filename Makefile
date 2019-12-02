#!/usr/bin/make -f

DOCKER_COMPOSE_CI = docker-compose
DOCKER_COMPOSE_DEV = docker-compose -f docker-compose.yml -f docker-compose.dev.override.yml
DOCKER_COMPOSE = $(DOCKER_COMPOSE_CI)

VENV = venv
PIP = $(VENV)/bin/pip
PYTHON = PYTHONPATH=dags $(VENV)/bin/python


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
	SLUGIFY_USES_TEXT_UNIDECODE=yes $(PIP) install -r requirements.txt
	$(PIP) install -r requirements.dev.txt
	$(PIP) install -e . --no-deps

dev-venv: venv-create dev-install


dev-flake8:
	$(PYTHON) -m flake8 peerscout dags tests

dev-pylint:
	$(PYTHON) -m pylint peerscout dags tests

dev-lint: dev-flake8 dev-pylint

dev-unittest:
	$(PYTHON) -m pytest -p no:cacheprovider $(ARGS) tests/unit_test

dev-dagtest:
	$(PYTHON) -m pytest -p no:cacheprovider $(ARGS) tests/dag_validation_test


dev-integration-test:
	pip install -e .  --no-dependencies
	airflow upgradedb
	$(PYTHON) -m pytest -p no:cacheprovider $(ARGS) tests/integration_test

dev-test: dev-lint dev-unittest dev-dagtest


build:
	$(DOCKER_COMPOSE) build peerscout-dags-image


build-dev:
	$(DOCKER_COMPOSE) build peerscout-dags-dev


ci-test-exclude-e2e: build-dev
	$(DOCKER_COMPOSE) run --rm peerscout-dags-dev ./run_test.sh


ci-end2end-test: build-dev
	$(DOCKER_COMPOSE) run --rm  test-client ./run_test.sh with-end-to-end
	$(DOCKER_COMPOSE) down -v

dev-env: build-dev
	$(DOCKER_COMPOSE_DEV) up  scheduler

ci-clean:
	$(DOCKER_COMPOSE) down -v



