# Dataclass containing application state information, is global and shared across everything

from dataclasses import dataclass

from typing import Optional
from cider.utils.shifter_config_reader import ShifterConfigReader
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper

@dataclass
class ShifterInterfaceState:
    interface_config: ShifterConfigReader
    apparatus: Optional[str] = None
    use_local: Optional[bool] = False
    session_name: Optional[str] = None
    oks_configuration: Optional[str] = None
    dummy_oks_configuration: Optional[ConfigurationWrapper] = None
    saved_configuration: Optional[str] = None