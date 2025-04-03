# Dataclass containing application state information, is global and shared across everything

from dataclasses import dataclass

from typing import Optional
from runconf_ui.utils.shifter_config_reader import ShifterConfigReader
from runconf_ui.interfaces.controller.config_wrapper import ConfigurationWrapper


@dataclass
class ShifterInterfaceState:
    # YAML used to configure the interface
    interface_config: ShifterConfigReader
    # NP02/NP04
    apparatus: Optional[str] = None
    # Do we want to use the local configuration? Only use if you're an expert!
    use_local: Optional[bool] = False
    # Currently selected configuration, not necessarily the open one
    oks_configuration: Optional[str] = None
    # Name of session in config
    session_name: Optional[str] = None
    # Currently open configuration
    dummy_oks_configuration: Optional[ConfigurationWrapper] = None
    # Configuration name we're going to save
    saved_configuration: Optional[str] = None
