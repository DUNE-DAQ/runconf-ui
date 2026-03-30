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
from runconf_ui.utils import check_config_has_session


class RemoteRepoManager(RepoManagerInterface):
    def __init__(
        self,
        apparatus: str,
        conf_directory: Path,
        config_file_name: str,
        operation_url: str,
        base_url: str,
    ):
        super().__init__(apparatus, conf_directory)
        if operation_url is None or base_url is None:
            raise RunConfToolsRepoException(
                f"Operation URL ({operation_url}) or Base URL ({base_url}) not set"
            )

        self._check_access(base_url)
        self._check_access(operation_url)

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
        """
        Get the list of DAQ versions
        """
        return self.conf_pool.get_daq_versions()

    def get_daq_sessions(self) -> list[str]:
        """
        Get the list of DAQ configurations
        """
        if self.daq_version is None:
            return []

        return self.conf_pool.get_confs(re.compile(f"^{self.daq_version}$"))

    def select_config(self, conf: str) -> Configuration:
        """
        checkout the ops repo and see the config is there
        """

        if self.daq_version is None:
            raise DaqVersionException("No DAQ release selected")

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
                f"{file_path} does not contain a session {self.daq_version}"
            )

        return file_path

    @classmethod
    def _check_access(cls, url: str):
        ...
        # os.environ["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"
        # g = Git()
        # g.ls_remote(url)
        # get_logger().info(f"Repo {url} is accessible")
