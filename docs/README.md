# DAQ TUI Interfaces
<!-- ### Names [Delete]
- LAGER: [Lightweight Access Gateway for Experimental Runs]
- BREW: [Basic Runtime Enable/disable Widget]
- GROG [General Runtime Operations Gateway] -->

## Shifter Interface

### Overview
The Shifter-Interface is a TUI designed to be used to enable/disable elements of the detector. Currently it can interface with 3 elements

- **Detector Subsystems**: These are large scale elements of the detector possibly consisting of many components, for example the NP04 APAs.
- **Dataflow Applications**: Straightforwardly, these are simply the applications which control dataflow from the detector
- **Triggers**: Specifically triggers controlled by detector components i.e. TPG in ReadoutApplications.

### Install
The TUI is installable with a daq enviroment through with pip
```bash
pip install [-e] .
```

### Initialisation
The interface is initialised with 
```bash
shifter-view
```
optionally the following flags exist for custom paths:
```
 [-d/--input-directory path/to/files] [-o/--output-directory /path/to/output] [-c/--interface_config interface configuration]
```
By default, the input directory points to `DUNEDAQ_DB_PATH`, the output directory the current working directory, and the interface config is https://github.com/DUNE-DAQ/cider/blob/develop/src/cider/configuration/np02_configuration.yml. This configuration is used to define trigger and detector subsystems.

 
### Usage
To get started, select a file from the dropdown menu and then select a session to modify. Press "open" to load the session.

Currently there are 3 categories of objects that can be enabled or disabled:
- **Detector subsystems**: For example the APAs, PDS, etc.
- **The Trigger System**: Triggers to enable/disable including trigger primitive generation
- **Dataflow applications**: Objects that control dataflow

To disable/enable items simply press the buttons on the left side of the screen. Each set of objects is given its own tab.
In addition, we provide 3 views of the detector configuration, although this is mostly intended for expert use.
- **Configuration view**: View a tree describing detector configuration
- **Detector system view**: Summary of detector subsystems which are enabled/disabled
- **Trigger View**: A summary of triggers/trigger objects which are enabled/disabled 

Once you have made the desired changes, press the "Create" button to save the configuration. By default the current configuration is saved in the <RUN FOLDER>/current_config directory.
Older configurations are automatically moved to <RUN FOLDER>/old_configs/run_<DATE> when a new configuration is saved. 

If you are unhappy with changes + want to revert to the original configuration, press the "Reset" button.

Finally to quit the interface, press the "Quit" button. The configuration can be run in drunc using the command provided after quitting.

If you have any questions, please contact the DAQ shifter on duty. Enjoy your shift!
