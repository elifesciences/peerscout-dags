import logging
from typing import Iterable, Optional, Union

from google.cloud import bigquery

LOGGER = logging.getLogger(__name__)


class BqQueryResult:
    def __init__(self, row_iterator: bigquery.table.RowIterator):
        self.row_iterator = row_iterator
        self.total_rows = row_iterator.total_rows

    def __iter__(self):
        for row in self.row_iterator:
            yield dict(row)


# pylint: disable=too-few-public-methods
class BqQuery:

    def __init__(self, project_name: Optional[str] = None):
        self.bigquery_client = bigquery.Client(project=project_name)

    def simple_query(
            self,
            query_template: str,
            gcp_project: str,
            dataset: str,
            table: Optional[str] = None,
            latest_state_value: Optional[str] = None
    ) -> Union[BqQueryResult, Iterable[dict]]:
        _query = query_template.format(
            project=gcp_project, dataset=dataset, table=table,
            latest_state_value=latest_state_value
        ).strip()
        LOGGER.debug("running query:\n%s", _query)
        query_job = self.bigquery_client.query(_query)
        return BqQueryResult(query_job.result())
