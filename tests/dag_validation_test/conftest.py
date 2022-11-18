"""
conftest
by m.owonibi
"""
import os
from airflow.models import dagbag
import pytest


DAG_PATH = os.path.join(os.path.dirname(__file__), "../..", "dags")
DAG_FILES = [f for f in os.listdir(DAG_PATH) if f.endswith("pipeline.py")]


@pytest.fixture(name="dagbag", scope="session")
def _airflow_dagbag() -> dagbag.DagBag:
    return dagbag.DagBag(dag_folder=DAG_PATH, include_examples=False)
