"""
utility for running queries in bigquery db
"""
import logging
from typing import List

from google.cloud import bigquery

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class BqQuery:
    """
    class for running queries in bigquery db
    """
    def __init__(self):
        self.bigquery_client = bigquery.Client()

    def simple_query(
            self,
            query: str,
            project: str,
            dataset: str
    ) -> List[dict]:
        """
        :param query:
        :param project:
        :param dataset:
        :return:
        """
        _query = query.format(project=project, dataset=dataset).strip()
        LOGGER.debug("running query:\n%s", _query)
        query_job = self.bigquery_client.query(_query)
        rows = [dict(row) for row in query_job]
        LOGGER.debug("rows: %s", rows)
        return rows
