#!/bin/bash

set -e

# avoid issues with .pyc/pyo files when mounting source directory
export PYTHONOPTIMIZE=


echo "running flake8"
python -m flake8 tests/ peerscout/

echo "running pylint"
PYLINTHOME=/tmp/datahub-dags-pylint \
python -m pylint tests/ peerscout/ --init-hook="import sys; sys.setrecursionlimit(1500)"

echo "running mypy"
python -m mypy --check-untyped-defs peerscout tests

echo "running unit tests"
python -m pytest tests/unit_test/ -p no:cacheprovider -s --disable-warnings

if [[ $1  &&  $1 == "with-end-to-end" ]]; then
    echo "running end to end tests"
    python -m pytest tests/end2end_test/ -p no:cacheprovider --log-cli-level=INFO
fi

echo "done"
