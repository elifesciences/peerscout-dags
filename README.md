# PeerScout DAGs

## Development

### Build the Image

```bash
make airflow-build
```

### Run the Pipeline

```bash
make data-hub-pipelines-run-keyword-extraction
```

### Run with particular development extraction config

For example (replace with desired development environment):

```bash
PEERSCOUT_DAGS_DEPLOYMENT_ENV=my_dev \
PEERSCOUT_DAGS_CONFIG=./dev-config/peerscout-keyword-extraction-data-pipeline-editor-provided-keywords.config.yaml \
make data-hub-pipelines-run-keyword-extraction
```