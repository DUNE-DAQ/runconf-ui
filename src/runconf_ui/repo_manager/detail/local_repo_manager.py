from pathlib import Path

from runconf_ui.exceptions import DaqVersionException
from runconf_ui.repo_manager.repo_manager_interface import RepoManagerInterface
from runconf_ui.utils import get_configs_with_session


class LocalRepoManager(RepoManagerInterface):
    def __init__(self, apparatus: str, conf_directory: Path):
        super().__init__(apparatus, conf_directory)
        self._available_versions = [conf_directory]
        self.set_daq_version(conf_directory)

    def get_available_daq_versions(self) -> list[Path]:
        return self._available_versions

    def get_daq_sessions(self) -> list[Path]:
        if self.daq_version is None:
            return []
        return get_configs_with_session(self.daq_version)

    def select_config(self, config: Path) -> Path:
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
