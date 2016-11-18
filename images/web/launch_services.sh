#!/bin/bash
echo "RUNNING SERVICES (Only gunicorn) :("
CODE_PATH="/home/$NB_USER/work"
WORKING_DIR_EX="$CODE_PATH/rest-service/"
cd $WORKING_DIR_EX
echo "$WORKING_DIR_EX"

echo "Launch gunicorn"
exec gunicorn -b 0.0.0.0:8000 routes:app --reload -t 120
