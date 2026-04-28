import re
from pathlib import Path

from conffwk import Configuration
from runconftools.ConfPool import ConfPool

from runconf_ui.exceptions import (
    ConfigBrokenInRepoException,
    ConfigNotFoundInRepoException,
    DaqVersionException,
    RunConfToolsRepoException,
)
from runconf_ui.repo_manager.repo_manager_interface import RepoManagerInterface
from runconf_ui.utils import check_config_has_session, get_logger


class RemoteRepoManager(RepoManagerInterface[str]):
    """Repository manager for remote git-based DAQ configuration repositories.

    Manages DAQ configurations stored in remote git repositories via the
    runconftools ConfPool interface.
    """

    def __init__(
        self,
        apparatus: str,
        conf_directory: Path,
        config_file_name: str,
        operation_url: str,
        base_url: str,
    ):
        """Initialize the remote repository manager.

        :param apparatus: The DAQ apparatus name
        :param conf_directory: Local directory to cache configurations
        :param config_file_name: Default config filename to load
        :param operation_url: URL of the operations git repository
        :param base_url: URL of the base git repository
        :raises RunConfToolsRepoException: If URLs are not set or ConfPool initialization fails
        """
        super().__init__(apparatus, conf_directory)
        if operation_url is None or base_url is None:
            raise RunConfToolsRepoException(
                f"Operation URL ({operation_url}) or Base URL ({base_url}) not set"
            )

        self.conf_directory.mkdir(parents=True, exist_ok=True)
        self.conf_pool = ConfPool(
            str(self.conf_directory), apparatus, operation_url, base_url
        )

        self.config_file_name = config_file_name

        if self.conf_pool is None:
            raise RunConfToolsRepoException(
                f"Cannot set up runconftools.ConfPool with operation url: {operation_url}, base url: {base_url}, apparatus: {apparatus}"
            )

    def get_available_daq_versions(self) -> list[str]:
        """Get the list of available DAQ versions from the remote repository.

        :returns: List of available DAQ version identifiers
        :rtype: list[str]
        """
        return self.conf_pool.get_daq_versions()

    def get_daq_sessions(self) -> list[str]:
        """Get the list of DAQ configurations for the current version.

        :returns: List of configuration names for the current DAQ version
        :rtype: list[str]
        """
        if self.daq_version is None:
            return []

        return self.conf_pool.get_confs(re.compile(f"^{self.daq_version}$"))

    def select_config(self, conf: str) -> Configuration:
        """Checkout and select a configuration from the remote repository.

        :param conf: The configuration name to select
        :returns: Path to the local cached configuration file
        :rtype: Configuration
        :raises DaqVersionException: If no DAQ version is selected
        :raises ConfigNotFoundInRepoException: If the config file is not found in the repository
        :raises ConfigBrokenInRepoException: If the config does not contain a valid session
        """
        if self.daq_version is None:
            raise DaqVersionException("No DAQ release selected")

        get_logger().info(
            "Checking out config %s for DAQ version %s", conf, self.daq_version
        )

        self.conf_pool.checkout_conf(conf, self.daq_version)  # type: ignore

        # Can save some time here
        file_path = next(self.conf_directory.rglob(self.config_file_name), None)

        if file_path is None:
            raise ConfigNotFoundInRepoException(
                f"Cannot find {self.config_file_name} in {self.daq_version}"
            )

        # Check session
        if not check_config_has_session(file_path):
            raise ConfigBrokenInRepoException(
                f"{file_path} does not contain a session!"
            )

        return file_path

    @property
    def default_version(self) -> str:
        return self.conf_pool.get_release()
