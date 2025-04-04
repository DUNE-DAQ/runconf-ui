# Dataclass containing application state information, is global and shared across everything
from dataclasses import dataclass
from typing import Optional

from runconf_ui.utils.shifter_config_reader.shifter_config_reader import ShifterConfigReader
from runconf_ui.interfaces.controller.daq_conf_wrapper import DaqConfigurationWrapper

@dataclass
class ShifterInterfaceState:
    '''
    Dataclass containing application state information, is global and shared across everything
    '''
    # YAML used to configure the interface
    interface_config: ShifterConfigReader
    # NP02/NP04
    apparatus: Optional[str] = None
    # Do we want to use the local configuration? Only use if you're an expert!
    use_local: Optional[bool] = False
    # Currently selected configuration, not necessarily the open one
    current_daq_config: Optional[str] = None
    # Name of session in config
    session_name: Optional[str] = None
    # Currently open configuration
    buffer_daq_config: Optional[DaqConfigurationWrapper] = None
    # Configuration name we're going to save
    saved_configuration: Optional[str] = None
    # current state of objects
    current_state: Optional[dict] = None