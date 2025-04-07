# Make backwards compatible with runconftools
try:
    from runconftools.ConfPool import ConfPool
except ImportError:
    from config_management.ConfPool import ConfPool
except Exception:
    raise ImportError(
        "Could not import runconftool or config_management. Please install runconftools or config_management"
    )

from runconf_ui.utils.daq_conf_tools.daq_conf_path_reader import DaqConfPathReader
from runconf_ui.interfaces.controller.application_controller import (
    ShifterInterfaceState,
)
from runconf_ui.utils.daq_conf_management_tools.management_interface import ManagementInterface

import re
from pathlib import Path


class RemoteDaqConfManager(ManagementInterface):
    def __init__(self, application_controller: ShifterInterfaceState):
        """
        Initialize the remote management interface
        """
        super().__init__(application_controller)

        if application_controller.apparatus is None:
            raise ValueError(
                "Apparatus not set! Please set the APPARATUS in your env or use the --apparatus flag"
            )

        self.conf_pool = ConfPool(
            self.application_controller.shifter_interface_config.download_directory,
            apparatus=application_controller.apparatus,
            operation_url=self.application_controller.shifter_interface_config.operation_url,
            base_url=self.application_controller.shifter_interface_config.base_url,
        )

    def get_daq_versions(self) -> list[str]:
        """
        Get the list of DAQ versions
        """
        return self.conf_pool.get_daq_versions()

    def get_configurations(self) -> list[str]:
        """
        Get the list of DAQ configurations
        """
        if self._daq_version == "":
            return []

        return self.conf_pool.get_confs(re.compile(f"^{self._daq_version}$"))

    def open_file(self, daq_configuration: str):
        self.conf_pool.checkout_conf(daq_configuration, self._daq_version)

        # Now we can open the file
        config_path_reader = DaqConfPathReader(
            self.application_controller.shifter_interface_config.default_config,
            self.application_controller.shifter_interface_config.session_name,
        )
        config_file = config_path_reader(
            self.application_controller.shifter_interface_config.download_directory
        )[0]

        if config_file is None:
            raise ValueError(f"Could not find config file for {daq_configuration}")

        return super().open_file(Path(config_file))


