# Dataclass containing application state information, is global and shared across everything
from dataclasses import dataclass, field
from typing import Optional

from runconf_ui.runconf_ui_configuration.shifter_config_reader import ShifterConfigReader
from runconf_ui.daq_config_interfaces.daq_config_file_io.daq_config_wrapper import DaqConfigurationWrapper

@dataclass
class ShifterInterfaceState:
    '''
    Dataclass containing application state information, should be shared across everything
    '''
    # YAML used to configure the interface
    shifter_interface_config: ShifterConfigReader
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
    current_state: dict = field(default_factory=lambda: {})