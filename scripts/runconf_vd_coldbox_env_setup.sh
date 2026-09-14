#!/bin/bash

export APPARATUS="vd_coldbox"

export SESSION_FILE="vd-coldbox-session.data.xml"

: "${DBT_AREA_ROOT:?DBT_AREA_ROOT must be set before sourcing this script}"
export CONFIG_DIR="${DBT_AREA_ROOT}/vd-coldbox-runs"

export OPERATION_URL="https://gitlab.cern.ch/dune-daq/online/vd-coldbox-configs-operation.git"
export BASE_URL="https://gitlab.cern.ch:7999/dune-daq/online/ehn1-daqconfigs.git"
