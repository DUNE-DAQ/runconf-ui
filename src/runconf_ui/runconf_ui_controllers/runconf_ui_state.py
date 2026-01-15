# Dataclass containing application state information, is global and shared across everything
from dataclasses import dataclass, field
from pathlib import Path

from runconf_ui.daq_config_interfaces.daq_config_file_io.daq_config_wrapper import (
    DaqConfigurationWrapper,
)
from runconf_ui.runconf_ui_configuration.shifter_config_reader import (
    ShifterConfigReader,
)


@dataclass
class ShifterInterfaceState:
    """
    Dataclass containing application state information, should be shared across everything
    """

    # YAML used to configure the interface
    shifter_interface_config: ShifterConfigReader
    # NP02/NP04
    apparatus: str | None = None
    # Do we want to use the local configuration? Only use if you're an expert!
    use_local: bool | None = False
    # Currently selected configuration, not necessarily the open one
    current_daq_config: str | None = None
    # Name of session in config
    session_name: str | None = None
    # Currently open configuration
    buffer_daq_config: DaqConfigurationWrapper | None = None
    # Configuration name we're going to save 
    saved_configuration: str | None = None
    # current state of objects
    current_state: dict = field(default_factory=lambda: {})

    @property
    def direct_config_path(self) -> Path:
        """
        Get the path to the configuration file
        """
        return Path(
            f"{self.shifter_interface_config.daq_config_directory}/{self.shifter_interface_config.default_config}"
        )
