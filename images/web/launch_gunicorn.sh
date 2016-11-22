#!/bin/bash
echo "RUNNING GUNICORN"
ls -laR /home/$CONDA_USER
CODE_PATH="/home/$CONDA_USER/work"
DATASETS_PATH="$CODE_PATH/datasets/"
export $DATASETS_PATH
WORKING_DIR_EX="$CODE_PATH/rest-service/"
cd $WORKING_DIR_EX
echo "$WORKING_DIR_EX"

echo "Launch gunicorn"
exec gunicorn -b 0.0.0.0:8000 routes:app --reload -t 120 --log-level debug --access-logfile '-'
