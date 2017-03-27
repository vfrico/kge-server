#!/bin/bash
echo "*** RUNNING GUNICORN"
CODE_PATH="/home/$CONDA_USER/kge-server"
cd $CODE_PATH

echo "*** Installing deps"
python3 setup.py install
echo "*** end installing"

DATASETS_PATH="$CODE_PATH/datasets/"
export $DATASETS_PATH
WORKING_DIR_EX="$CODE_PATH/rest-service/"
cd $WORKING_DIR_EX
echo "$WORKING_DIR_EX"

echo "*** Launch gunicorn"
exec gunicorn -b 0.0.0.0:8000 routes:app -w 4 --threads 4 --reload -t 120 --log-level debug --access-logfile '-'
