from pathlib import Path

from runconf_ui.exceptions import DaqVersionException
from runconf_ui.repo_manager.repo_manager_interface import RepoManagerInterface
from runconf_ui.utils import get_configs_with_session


class LocalRepoManager(RepoManagerInterface[Path]):
    """Repository manager for local file-based configuration repositories.

    Manages DAQ configurations stored in a local file system directory.
    """

    def __init__(
        self, apparatus: str, conf_directory: Path, config_file_name: str | None = None
    ):
        """Initialize the local repository manager.

        :param apparatus: The DAQ apparatus name
        :param conf_directory: Path to the local configuration directory
        """
        super().__init__(apparatus, conf_directory)
        self._available_versions = [conf_directory]
        self.set_daq_version(conf_directory)

        self.conf_file = config_file_name

    def get_available_daq_versions(self) -> list[Path]:
        """Get the list of available DAQ versions.

        For local repository, this returns the configuration directory path.

        :returns: List containing the configuration directory
        :rtype: list[Path]
        """
        return self._available_versions

    def get_daq_sessions(self) -> list[Path]:
        """Get the list of available DAQ sessions.

        :returns: List of paths to configuration files for the current version
        :rtype: list[Path]
        """
        if self.daq_version is None:
            return []

        confs_w_ses = get_configs_with_session(self.daq_version)

        if self.conf_file is None:
            return confs_w_ses

        return [c for c in confs_w_ses if c.name == self.conf_file]

    def select_config(self, config: Path) -> Path:
        """Select a configuration file by path or name.

        Attempts direct path match first, then falls back to matching by filename.

        :param config: The path or filename of the configuration to select
        :returns: The full path to the selected configuration file
        :rtype: Path
        :raises DaqVersionException: If the configuration is not found
        """
        sessions = self.get_daq_sessions()

        # Direct match first.
        if config in sessions:
            return config

        # Fall back to matching by filename only.
        match = next((p for p in sessions if p.name == config), None)
        if match is not None:
            return match

        raise DaqVersionException(
            f"Session {config} does not exist for {self.daq_version}"
        )
