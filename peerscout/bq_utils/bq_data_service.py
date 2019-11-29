"""
bq data service
written by tayowonibi
"""

import logging
import os
from google.cloud import bigquery
from google.cloud.bigquery import LoadJobConfig, Client
from google.cloud.bigquery import (SourceFormat, WriteDisposition)
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-arguments
def load_file_into_bq(
        filename: str,
        dataset_name: str,
        table_name: str,
        source_format=SourceFormat.NEWLINE_DELIMITED_JSON,
        write_mode=WriteDisposition.WRITE_APPEND,
        auto_detect_schema=True,
        rows_to_skip=0,
):
    """
    :param auto_detect_schema:
    :param filename:
    :param dataset_name:
    :param table_name:
    :param source_format:
    :param rows_to_skip:
    :param write_mode:
    :return:
    """
    if os.path.isfile(filename) and os.path.getsize(filename) == 0:
        LOGGER.info("File %s is empty.", filename)
        return
    client = Client()
    dataset_ref = client.dataset(dataset_name)
    table_ref = dataset_ref.table(table_name)
    job_config = LoadJobConfig()
    job_config.source_format = source_format
    job_config.write_disposition = write_mode
    job_config.autodetect = auto_detect_schema
    if source_format is bigquery.SourceFormat.CSV:
        job_config.skip_leading_rows = rows_to_skip
    with open(filename, "rb") as source_file:

        job = client.load_table_from_file(
            source_file, destination=table_ref, job_config=job_config
        )

        # Waits for table cloud_data_store to complete
        job.result()
        LOGGER.info(
            "Loaded %s rows into %s:%s.",
            job.output_rows,
            dataset_name,
            table_name
        )
