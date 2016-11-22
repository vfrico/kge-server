#!/bin/bash
echo "RUNNING CELERY"
ls -laR /home/$CONDA_USER
CODE_PATH="/home/$CONDA_USER/work"
WORKING_DIR_EX="$CODE_PATH/rest-service/"
cd $WORKING_DIR_EX
echo "$WORKING_DIR_EX"

echo "Launch celery"
export C_FORCE_ROOT=True
exec celery -A async_server worker -l info
