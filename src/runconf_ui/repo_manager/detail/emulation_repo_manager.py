from pathlib import Path

from runconftools.ConfPool import ConfPool

from runconf_ui.exceptions import (
    DaqVersionException,
    RunConfToolsRepoException,
)
from runconf_ui.repo_manager.repo_manager_interface import RepoManagerInterface
from runconf_ui.utils import get_configs_with_session, get_logger


class EmulationRepoManager(RepoManagerInterface[Path]):
    """Repository manager for remote git-based DAQ configuration repositories.
    But, contrary to the remote one, this interfaces with the base repository as it's only for emulation

    Manages DAQ configurations stored in remote git repositories via the
    runconftools ConfPool interface.
    """

    def __init__(
        self,
        apparatus: str,
        conf_directory: Path,
        operation_url: str,  ## MR: this is in some way a problem of ConfPool, we should envision a mode in which the operation is not necessary
        base_url: str,
        config_file_names: list[str],
    ):
        """Initialize the remote repository manager.

        :param apparatus: The DAQ apparatus name
        :param conf_directory: Local directory to cache configurations
        :param config_file_name: List of config filename to load to mask only emulation files.
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

        if not config_file_names:
            raise RunConfToolsRepoException(
                "config_file_name must be specified for emulation mode"
            )
        self.config_file_names = config_file_names

    def get_available_daq_versions(self) -> list[str]:  # type: ignore[override]
        """Get the list of available DAQ versions from the remote repository.

        :returns: List of available DAQ version identifiers
        :rtype: list[str]
        """
        return self.conf_pool.get_base_branches()  

    def get_daq_sessions(self) -> list[Path]:
        """Get the list of DAQ configurations for the current version.

        :returns: List of configuration names for the current DAQ version
        :rtype: list[str]

        Specifically this means getting all the configuration file with a session
        """
        if self.daq_version is None:
            return []

        return self.get_emulation_configurations(self.conf_directory)

    def select_config(self, config: Path) -> Path:
        """Select a configuration file by path or name.

        Attempts direct path match first, then falls back to matching by filename.
        :param config: The path or filename of the configuration to select
        :returns: The full path to the selected configuration file
        :rtype: Path
        :raises DaqVersionException: If the configuration is not found
        """

        sessions = (
            self.get_daq_sessions()
        )  ## in this case if feels a bit redundant, can we remove it?

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

    def set_daq_version(self, version: str | None):
        super().set_daq_version(version)
        if version is not None:
            self.conf_pool.checkout_base(version)
    
    @property
    def default_version(self) -> str:
        return self.conf_pool.get_release()

    def get_emulation_configurations(self, config_path: Path) -> list[Path]:
        confs = get_configs_with_session(config_path)

        return [c for c in confs if c.name in self.config_file_names]
