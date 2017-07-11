#!/bin/bash
echo "*** RUNNING CELERY"
CODE_PATH="/home/$CONDA_USER/kge-server"
cd $CODE_PATH

echo "*** Installing deps"
python3 setup.py install
echo "*** end installing"

WORKING_DIR_EX="$CODE_PATH/rest-service/"
DATASETS_PATH="$CODE_PATH/datasets/"
cd $WORKING_DIR_EX
echo "$WORKING_DIR_EX"

echo "*** Launch celery"
export C_FORCE_ROOT=True
export SQLITE_DATABASE_FILE_PATH="$DATASETS_PATH/server.db"
export $DATASETS_PATH
exec celery -A async_server worker -l info
