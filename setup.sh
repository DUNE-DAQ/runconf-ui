#!/bin/bash

HERE=${BASH_SOURCE[0]:-${(%):-%x}}
export CIDER=$(cd $(dirname ${HERE}) && pwd)
echo "Setting up CIDER from $CIDER_DIR`"
cd $CIDER_DIR && pip install -e . && cd -
# export CIDER_DATA=${CIDER_DIR}/data
echo "CIDER setup done"
