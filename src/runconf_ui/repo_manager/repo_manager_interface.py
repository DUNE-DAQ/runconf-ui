from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

from runconf_ui.exceptions import DaqVersionException, MissingRunconfUIConfigException

T = TypeVar("T")


class RepoManagerInterface(ABC, Generic[T]):
    """Abstract base class for repository managers.

    Defines the interface for managing DAQ configuration repositories,
    including version and session selection.
    """

    def __init__(self, apparatus: str, conf_directory: Path):
        """Initialize the repository manager.

        :param apparatus: The DAQ apparatus name (e.g., 'NP02', 'NP04')
        :param conf_directory: Path to the configuration directory
        """
        self.apparatus = apparatus
        self.conf_directory = conf_directory
        self.daq_version: T | None = None

    @abstractmethod
    def get_available_daq_versions(self) -> list[T]:
        """Get the list of available DAQ versions.

        :returns: List of available DAQ version identifiers
        :rtype: list[T]
        """
        ...

    def set_daq_version(self, version: T | None):
        """Set the current DAQ version.

        :param version: The DAQ version to set
        :raises DaqVersionException: If the version is not in the available versions list
        """
        if version not in self.get_available_daq_versions() and version is not None:
            raise DaqVersionException(
                f"{version} not in the available list of available DAQ versions ({self.get_available_daq_versions})"
            )
        self.daq_version = version

    @abstractmethod
    def get_daq_sessions(self) -> list[T]:
        """Get the list of available DAQ sessions for the current version.

        :returns: List of available session identifiers
        :rtype: list[T]
        """
        ...

    def get_runconf_ui_config_path(self):
        """Get the path to the runconf-ui configuration file for the apparatus.

        :returns: Path to the runconf-ui settings YAML file
        :raises MissingRunconfUIConfigException: If the config file does not exist
        """
        ui_config = (
            self.conf_directory / "runconf-ui-settings" / f"{self.apparatus}.yml"
        )
        if not ui_config.exists():
            raise MissingRunconfUIConfigException(
                f"{self.conf_directory} does not contain 'runconf-ui-settings/{self.apparatus}.yml'"
            )
        return ui_config

    @abstractmethod
    def select_config(self, session: T) -> T:
        """Select a configuration file for the given session.

        :param session: The session identifier to select
        :returns: Path or identifier to the selected configuration
        :rtype: T
        """
        ...
