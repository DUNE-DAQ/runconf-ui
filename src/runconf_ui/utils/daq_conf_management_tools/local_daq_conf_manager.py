from pathlib import Path
from runconf_ui.utils.daq_conf_management_tools.management_interface import ManagementInterface
from runconf_ui.utils.daq_conf_tools.daq_conf_path_reader import DaqConfPathReader
from runconf_ui.interfaces.controller.application_controller import (
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

        return DaqConfPathReader(
            str(self.application_controller.shifter_interface_config.default_config),
            str(self.application_controller.shifter_interface_config.session_name),
        )(self._daq_version)
