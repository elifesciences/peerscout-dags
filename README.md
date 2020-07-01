# PeerScout DAGs

## Development

### Start with particular development extraction config

For example (replace with desired development environment):

```bash
PEERSCOUT_DAGS_DEPLOYMENT_ENV=my_dev \
PEERSCOUT_DAGS_CONFIG=./dev-config/peerscout-keyword-extraction-data-pipeline-editor-provided-keywords.config.yaml \
make \
  airflow-build airflow-stop airflow-start airflow-logs
```

Airflow should be available on [port 8084](http://localhost:8084/) (unless overridden via `PEERSCOUT_DAGS_AIRFLOW_PORT`).
