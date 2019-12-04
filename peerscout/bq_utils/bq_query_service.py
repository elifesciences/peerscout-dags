import logging
from typing import List

from google.cloud import bigquery

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class BqQuery:

    def __init__(self, project_name: str = None):
        self.bigquery_client = bigquery.Client(project=project_name)

    def simple_query(
            self,
            query: str,
            project: str,
            dataset: str,
            table: str = None
    ) -> List[dict]:
        _query = query.format(
            project=project, dataset=dataset, table=table
        ).strip()
        LOGGER.debug("running query:\n%s", _query)
        query_job = self.bigquery_client.query(_query)
        rows = [dict(row) for row in query_job]
        LOGGER.debug("rows: %s", rows)
        return rows
