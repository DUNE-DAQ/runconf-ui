"""
Simple wrapper for talking to config-management
"""

from config_management.ConfPool import ConfPool
from runconf_ui.utils.shifter_config_reader import ShifterConfigReader
from runconf_ui.utils.config_path_reader import ConfigPathReader
from runconf_ui.interfaces.controller.config_wrapper import ConfigurationWrapper
from runconf_ui.interfaces.controller.application_controller import ShifterInterfaceState
import runconf_ui.interfaces.actions.actions as ca
import logging

import re
from abc import ABC, abstractmethod
from pathlib import Path


class ManagementInterface(ABC):
    def __init__(self, app_controller: ShifterInterfaceState):
        """
        Initialize the management interface
        """
        self.app_controller = app_controller
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

    def open_file(self, file_path: Path) -> ConfigurationWrapper:
        self.file_name = file_path
        return ConfigurationWrapper(f"{file_path}")

    @classmethod
    def find_session(cls, file_name: str):
        config_file = ConfigurationWrapper(file_name)
        file_sessions = ca.GetDalsOfClassAction(config_file)("Session")
        if file_sessions:
            return ca.GetAttributeAction(config_file)(file_sessions[0], "id")
        else:
            return None


class RemoteManagementInterface(ManagementInterface):
    def __init__(self, app_controller: ShifterInterfaceState):
        """
        Initialize the remote management interface
        """
        super().__init__(app_controller)

        if app_controller.apparatus is None:
            raise ValueError(
                "Apparatus not set! Please set the APPARATUS in your env or use the --apparatus flag"
            )

        self.conf_pool = ConfPool(
            self.app_controller.interface_config.download_directory,
            apparatus=app_controller.apparatus,
            operation_url=self.app_controller.interface_config.operation_url,
            base_url=self.app_controller.interface_config.base_url,
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
        config_path_reader = ConfigPathReader(
            self.app_controller.interface_config.default_config,
            self.app_controller.interface_config.session_name,
        )
        config_file = config_path_reader(
            self.app_controller.interface_config.download_directory
        )[0]

        if config_file is None:
            raise ValueError(f"Could not find config file for {daq_configuration}")

        return super().open_file(Path(config_file))


class LocalManagementInterface(ManagementInterface):
    def __init__(self, app_controller: ShifterInterfaceState):
        """
        Initialize the local management interface
        """
        super().__init__(app_controller)

        self.config_directories = [
            Path(p)
            for p in f"{self.app_controller.interface_config.download_directory}".split(
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

        return ConfigPathReader(
            str(self.app_controller.interface_config.default_config),
            str(self.app_controller.interface_config.session_name),
        )(self._daq_version)
