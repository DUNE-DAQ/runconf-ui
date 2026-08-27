#!/bin/bash

export APPARATUS="np04_emu"

export SESSION_FILE="np04-emu-session.data.xml"

: "${DBT_AREA_ROOT:?DBT_AREA_ROOT must be set before sourcing this script}"
export CONFIG_DIR="${DBT_AREA_ROOT}/np04-emu-runs"

export OPERATION_URL="https://gitlab.cern.ch/dune-daq/online/np04-emu-configs.git"
export BASE_URL="ssh://git@gitlab.cern.ch:7999/dune-daq/online/ehn1-daqconfigs.git"
