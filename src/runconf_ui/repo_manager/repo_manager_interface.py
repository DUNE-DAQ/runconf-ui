from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

from runconf_ui.exceptions import DaqVersionException, MissingRunconfUIConfigException

T = TypeVar("T")


class RepoManagerInterface(ABC, Generic[T]):
    def __init__(self, apparatus: str, conf_directory: Path):
        self.apparatus = apparatus
        self.conf_directory = conf_directory
        self.daq_version: T | None = None

    @abstractmethod
    def get_available_daq_versions(self) -> list[T]: ...

    def set_daq_version(self, version: T | None):
        if version not in self.get_available_daq_versions() and version is not None:
            raise DaqVersionException(
                f"{version} not in the available list of available DAQ versions ({self.get_available_daq_versions})"
            )
        self.daq_version = version

    @abstractmethod
    def get_daq_sessions(self) -> list[T]: ...

    def get_runconf_ui_config_path(self):
        ui_config = (
            self.conf_directory / "runconf-ui-settings" / f"{self.apparatus}.yml"
        )
        if not ui_config.exists():
            raise MissingRunconfUIConfigException(
                f"{self.conf_directory} does not contain 'runconf-ui-settings/{self.apparatus}.yml'"
            )
        return ui_config

    @abstractmethod
    def select_config(self, session: T) -> T: ...
