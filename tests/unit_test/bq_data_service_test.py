from unittest.mock import patch
import pytest

from peerscout.utils.bq_data_service import (
    load_file_into_bq,
)
import peerscout.utils.bq_data_service \
    as bq_data_service_module


@pytest.fixture(name="mock_bigquery")
def _bigquery():
    with patch.object(bq_data_service_module, "bigquery") as mock:
        yield mock


@pytest.fixture(name="mock_bq_client_class")
def _bq_client():
    with patch.object(bq_data_service_module, "Client") as mock:
        yield mock


@pytest.fixture(name="mock_load_job_config")
def _load_job_config():
    with patch.object(bq_data_service_module, "LoadJobConfig") as mock:
        yield mock


@pytest.fixture(name="mock_open", autouse=True)
def _open():
    with patch.object(bq_data_service_module, "open") as mock:
        yield mock


@pytest.fixture(name="mock_path")
def _getsize():
    with patch.object(bq_data_service_module.os, "path") as mock:
        mock.getsize.return_value = 1
        mock.isfile.return_value = True
        yield mock


def test_load_file_into_bq(
        mock_load_job_config,
        mock_open,
        mock_bq_client_class):
    file_name = "file_name"
    dataset_name = "dataset_name"
    table_name = "table_name"
    load_file_into_bq(
        filename=file_name,
        dataset_name=dataset_name,
        table_name=table_name)

    mock_open.assert_called_with(file_name, "rb")
    source_file = mock_open.return_value.__enter__.return_value

    mock_bq_client_class.assert_called_once()
    mock_bq_client = mock_bq_client_class.return_value
    mock_bq_client.dataset.assert_called_with(dataset_name)
    mock_bq_client.dataset(
        dataset_name).table.assert_called_with(table_name)

    table_ref = mock_bq_client.dataset(
        dataset_name).table(table_name)
    mock_bq_client.load_table_from_file.assert_called_with(
        source_file, destination=table_ref,
        job_config=mock_load_job_config.return_value)
