FROM puckel/docker-airflow:1.10.4
ARG install_dev

USER root
RUN apt update && apt install sudo -yqq
RUN usermod -aG sudo airflow
RUN echo "airflow ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

RUN sed -i 's/LocalExecutor/SequentialExecutor/' /entrypoint.sh

# install spaCy separately to allow better caching of large language model download
COPY requirements.spacy.txt ./
RUN pip install --disable-pip-version-check -r requirements.spacy.txt

# download spaCy language models
RUN python -m spacy download en_core_web_lg
RUN if [ "${install_dev}" = "y" ]; then python -m spacy download en_core_web_sm; fi

COPY requirements.build.txt ./
RUN pip install --disable-pip-version-check -r requirements.build.txt

COPY requirements.txt ./
RUN pip install --disable-pip-version-check -r requirements.txt

USER airflow
ENV PATH /usr/local/airflow/.local/bin:$PATH
COPY --chown=airflow:airflow requirements.dev.txt ./
RUN if [ "${install_dev}" = "y" ]; then pip install --disable-pip-version-check --user -r requirements.dev.txt; fi

COPY --chown=airflow:airflow peerscout ./peerscout
COPY --chown=airflow:airflow dags ./dags
COPY --chown=airflow:airflow setup.py ./setup.py
RUN pip install -e . --user --no-dependencies

COPY .pylintrc ./.pylintrc
COPY --chown=airflow:airflow tests ./tests
COPY --chown=airflow:airflow run_test.sh ./
RUN if [ "${install_dev}" = "y" ]; then chmod +x run_test.sh; fi

COPY --chown=airflow:airflow worker.sh ./
RUN chmod +x worker.sh

RUN mkdir -p $AIRFLOW_HOME/serve
RUN ln -s $AIRFLOW_HOME/logs $AIRFLOW_HOME/serve/log

ENTRYPOINT []
