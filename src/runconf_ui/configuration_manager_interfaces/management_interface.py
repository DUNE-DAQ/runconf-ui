"""
Simple wrapper for talking to config-management
"""

from runconf_ui.daq_config_interfaces.daq_config_file_io.daq_config_wrapper import (
    DaqConfigurationWrapper,
)
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)
import runconf_ui.daq_config_interfaces.actions.actions as ca

import logging
from abc import ABC, abstractmethod
from pathlib import Path


class ManagementInterface(ABC):
    def __init__(self, application_controller: ShifterInterfaceState):
        """
        Initialize the management interface
        """
        self.application_controller = application_controller
        self.file_name = ""
        self._daq_version = ""

    @abstractmethod
    def get_daq_versions(self) -> list[str]:
        """
        Get the list of DAQ versions
        """
        pass

    def set_version(self, daq_version: str):
        """
        Set the DAQ version
        """
        self._daq_version = daq_version
        logging.info(f"Set DAQ version to {daq_version}")

    @property
    def daq_version(self) -> str:
        """
        Get the DAQ version
        """
        return self._daq_version

    def open_file(self, file_path: Path) -> DaqConfigurationWrapper:
        self.file_name = file_path
        return DaqConfigurationWrapper(f"{file_path}")

    @classmethod
    def find_session(cls, file_name: str):
        config_file = DaqConfigurationWrapper(file_name)
        file_sessions = ca.GetDalsOfClassAction(config_file)("Session")
        if file_sessions:
            return ca.GetAttributeAction(config_file)(file_sessions[0], "id")
        else:
            return None
