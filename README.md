# DAQ TUI Interfaces
<!-- ### Names [Delete]
- LAGER: [Lightweight Access Gateway for Experimental Runs]
- BREW: [Basic Runtime Enable/disable Widget]
- GROG [General Runtime Operations Gateway] -->

## Shifter Interface [LAGER]

### Overview
The Lightweight Access Gateway for Experimental Runs [LAGER] is a TUI designed to be used to enable/disable elements of the detector. Currently it can interface with 3 elements

- **Detector Subsystems**: These are large scale elements of the detector possibly consisting of many components, for example the NP04 APAs.
- **Dataflow Applications**: Straightforwardly, these are simply the applications which control dataflow from the detector
- **Triggers**: Specifically triggers controlled by detector components i.e. TPG in ReadoutApplications.

### Usage
