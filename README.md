# Runconf-UI
[![Run pytest](https://github.com/DUNE-DAQ/runconf-ui/actions/workflows/run_pytest.yml/badge.svg)](https://github.com/DUNE-DAQ/runconf-ui/actions/workflows/run_pytest.yml)

## Overview
Runconf-UI is provides a textual user interface to interact with DAQ configurations before starting a run. It allows for enabling/disabling detector elements as well as adjusting the values for trigger rates, etc.

Full documentation can be found here <>

## Install

The TUI is installable with a daq enviroment through with pip

```bash
pip install [-e] .
```

## Initialisation

The interface is initialised with

```bash
runconf-shifter-ui
```

optionally the following CLI flags exist for custom paths:

```
  -a, --apparatus                 Set the detector apparatus i.e. NP02/NP04
  
  -o, --output-directory          Set the directory for the configured configurations
  
  -d, --daq-config-directory      Where do you want to download configs
                                  to 

  -l, --use-local                 (Flag) Use a local configuration

  --help                          Show help
```

Remote Only Options
```
  -f, --config-file-name          Name of daq .data.xml config to find
  
  -b, --base-url                  Base URL for the interface, not used for
                                  local operation
  
  -r, --ops-url                   Operation URL for the interface, not used
                                  for local operation
  
  -d --log-level                  Set the debug log level
```
