FROM python:3.8-slim
ARG install_dev=n

USER root

ENV PIP_NO_CACHE_DIR=1

WORKDIR /peerscout

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

COPY requirements.dev.txt ./
RUN if [ "${install_dev}" = "y" ]; then pip install --disable-pip-version-check --user -r requirements.dev.txt; fi

COPY peerscout ./peerscout
COPY setup.py ./setup.py
RUN pip install -e . --user --no-dependencies

COPY tests ./tests
COPY .flake8 .pylintrc mypy.ini run_test.sh ./
