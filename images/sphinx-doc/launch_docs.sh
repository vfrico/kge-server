#!/bin/bash
echo "GENERATING DOCS"
CODE_PATH="/home/$CONDA_USER/kge-server"
cd $CODE_PATH
WORKING_DIR_EX="$CODE_PATH/doc/"
cd $WORKING_DIR_EX
echo "$WORKING_DIR_EX"

SPHINX_OPTS="$@"

echo "Launch sphinx"
exec make $SPHINX_OPTS
