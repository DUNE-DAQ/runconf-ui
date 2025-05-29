from pathlib import Path
from runconf_ui.configuration_manager_interfaces.management_interface import (
    ManagementInterface,
)
from runconf_ui.daq_config_interfaces.daq_config_file_io.daq_conf_path_reader import (
    DaqConfPathReader,
)
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)


class LocalDaqConfManager(ManagementInterface):
    def __init__(self, application_controller: ShifterInterfaceState):
        """
        Initialize the local management interface
        """
        super().__init__(application_controller)

        self.config_directories = [
            Path(p)
            for p in f"{self.application_controller.shifter_interface_config.download_directory}".split(
                ":"
            )
        ]

    def get_daq_versions(self) -> list[Path]:
        """
        Get the list of DAQ versions
        """
        return self.config_directories

    def get_configurations(self) -> list[Path]:
        """
        Get the list of DAQ configurations
        """
        if self._daq_version == "":
            return []

        return DaqConfPathReader()(self._daq_version)

    def get_default_version(self) -> str:
        """
        Get the default DAQ version
        """
        return ""
