FROM apache/airflow:2.3.0-python3.7
ARG install_dev=n

USER root

RUN sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 467B942D3A79BD29

RUN apt-get update \
  && apt-get install sudo gcc g++ -yqq \
  && rm -rf /var/lib/apt/lists/*

RUN usermod -aG sudo airflow
RUN echo "airflow ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

USER airflow

COPY requirements.build.txt ./
RUN pip install --disable-pip-version-check -r requirements.build.txt

# install spaCy separately to allow better caching of large language model download
COPY requirements.spacy.txt ./
RUN pip install --disable-pip-version-check -r requirements.spacy.txt

# download spaCy language models
RUN python -m spacy download en_core_web_lg
RUN if [ "${install_dev}" = "y" ]; then python -m spacy download en_core_web_sm; fi

COPY requirements.txt ./
RUN pip install --disable-pip-version-check -r requirements.txt

ENV PATH /home/airflow/.local/bin:$PATH
COPY --chown=airflow:airflow requirements.dev.txt ./
RUN if [ "${install_dev}" = "y" ]; then pip install --disable-pip-version-check --user -r requirements.dev.txt; fi

COPY --chown=airflow:airflow peerscout ./peerscout
COPY --chown=airflow:airflow dags ./dags
COPY --chown=airflow:airflow setup.py ./setup.py
RUN pip install -e . --user --no-dependencies

COPY --chown=airflow:airflow tests ./tests
COPY --chown=airflow:airflow .flake8 .pylintrc run_test.sh ./
RUN if [ "${install_dev}" = "y" ]; then chmod +x run_test.sh; fi

RUN mkdir -p $AIRFLOW_HOME/serve
RUN ln -s $AIRFLOW_HOME/logs $AIRFLOW_HOME/serve/log

ENTRYPOINT []
