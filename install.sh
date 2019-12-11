#!/bin/bash

set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

pip install  --user -r $DIR/requirements.spacy.txt
pip install  --user -r $DIR/requirements.txt
pip install -e $DIR/ --user --no-dependencies

python  -m spacy download en_core_web_lg --user

cp $DIR/dags $1 -r
