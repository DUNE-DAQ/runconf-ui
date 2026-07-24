#!/bin/bash

export APPARATUS="np02-emu"

export SESSION_FILE="np02-emu-session.data.xml"
export CONFIG_DIR="${DBT_AREA_ROOT}/np02-emu-runs"
: "${DBT_AREA_ROOT:?DBT_AREA_ROOT must be set before sourcing this script}"

export OPERATION_URL="https://gitlab.cern.ch/dune-daq/online/np02-configs-operation.git"
export BASE_URL="ssh://git@gitlab.cern.ch:7999/dune-daq/online/ehn1-daqconfigs.git"
