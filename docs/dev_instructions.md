# Instructions for Developers
## Overview
This is a rough guide for de-mistifying the runconf_ui interface! Note, if you just want to setup a new detector instructions are saved [here](shttps://github.com/DUNE-DAQ/runconf-ui/blob/develop/docs/shifter_interface_yaml.md). 

For specific questions about textual, please check [here](https://textual.textualize.io). 

## runconf_ui structure
1. apps: Application storage
2. configuration_manager_interfaces: Interfaces to find config files. This can either be for local or remotely stored configs
3. daq_config_interfaces: Specific interfaces with the configuration via conffwk. Includes a wrapper around the configuration as well as "actions" which define a common interface with the configuration.
4. runconf_ui_configuration: Two groups of objects. Firstly the shifter_config_reader which opens the runconf_ui YAML files. Seconly objects to extract detector information from the yamls
6. runconf_ui_controllers: Single class that contains state information about the entire interface
7. screens: Textual screens
8. utils: Generic utilities for handling files/environment
9. widgets: Textual widgets 

## Main Screen
The main interface (screen) presented o