"""
@author: mowonibi
"""
import os
from urllib.parse import urljoin
import re
import logging
import json
import requests

LOGGER = logging.getLogger(__name__)


# pylint: disable=no-else-return


class AirflowAPI:
    """
    test class
    """

    def __init__(self):
        airflow_host = os.getenv("AIRFLOW_HOST")
        airflow_port = os.getenv("AIRFLOW_PORT", "8080")
        self.airflow_url = "http://%s:%s" % (airflow_host, airflow_port)

    # pylint: disable=no-self-use
    def send_request(self, url, method="GET", json_param=None):
        """
        :param url:
        :param method:
        :param json_param:
        :return:
        """
        params = {
            "url": url,
        }
        if json_param is not None:
            params["json"] = json_param
        # pylint: disable=not-callable
        resp = getattr(requests, method.lower())(**params)
        if not resp.ok:
            # It is justified here because there might be many resp types.
            # noinspection PyBroadException
            try:
                data = resp.json()
            except Exception:  # pylint: disable=broad-except
                data = {}
            raise OSError(data.get("error", "Server error"))

        return resp.json()

    def unpause_dag(self, dag_id):
        """
        :param dag_id:
        :return:
        """

        return requests.get(
            "%s/api/experimental/dags/%s/paused/false" %
            (self.airflow_url, dag_id)
        )

    def pause_dag(self, dag_id):
        """
        :param dag_id:
        :return:
        """
        return requests.get(
            "%s/api/experimental/dags/%s/paused/true" %
            (self.airflow_url, dag_id)
        )

    def trigger_dag(self, dag_id, conf=None):
        """
        :param dag_id:
        :param conf:
        :return:
        """
        self.unpause_dag(dag_id)
        endpoint = "/api/experimental/dags/{}/dag_runs".format(dag_id)
        url = urljoin(self.airflow_url, endpoint)
        data = self.send_request(url, method="POST",
                                 json_param={"conf": conf, })

        pattern = r"\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d"
        return re.findall(pattern, data["message"])[0]

    def dag_state(self, dag_id, execution_date):
        """
        :param dag_id:
        :param execution_date:
        :return:
        """
        return requests.get(
            "%s/api/experimental/dags/%s/dag_runs/%s"
            % (self.airflow_url, dag_id, execution_date)
        )

    def is_dag_running(self, dag_id, execution_date):
        """
        :param dag_id:
        :param execution_date:
        :return:
        """
        response = self.dag_state(dag_id, execution_date)
        json_response = json.loads(response.text)
        if json_response.get("state").lower() == "running":
            return True

        return False

    def get_dag_status(self, dag_id, execution_date):
        """
        :param dag_id:
        :param execution_date:
        :return:
        """
        response = self.dag_state(dag_id, execution_date)
        json_response = json.loads(response.text)
        return json_response.get("state").lower()
