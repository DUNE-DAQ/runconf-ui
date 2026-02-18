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


class RemoteRepoManager(RepoManagerInterface[str]):
    def __init__(self, apparatus: str, conf_directory: Path, default_config_fle_name: str, operation_url: str, base_url: str):
        super().__init__(apparatus, conf_directory)
        if operation_url is None or base_url is None:
            raise RunConfToolsRepoException(f"Operation URL ({operation_url}) or Base URL ({base_url}) not set")
        
        self.conf_pool = ConfPool(
            str(self.conf_directory),
            apparatus,
            operation_url,
            base_url
        )
        
        self.default_config_fle_name = default_config_fle_name
        
        if self.conf_pool is None:
            raise RunConfToolsRepoException(f"Cannot set up runconftools.ConfPool with operation url: {operation_url}, base url: {base_url}, apparatus: {apparatus}")
    
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

    def select_config(self, conf: str)->Configuration:
        '''
        checkout the ops repo and see the config is there
        '''
        
        if self.daq_version is None:
            raise DaqVersionException("No DAQ release selected")
        
        self.conf_pool.checkout_conf(conf, self.daq_version)  # type: ignore
        
        # Can save some time here
        file_path = next(self.conf_directory.rglob(self.default_config_fle_name), None)
        
        if file_path is None:
            raise ConfigNotFoundInRepoException(f"Cannot find {self.default_config_fle_name} in {self.daq_version}")
        
        # Check session
        if not check_config_has_session(file_path):
            raise ConfigBrokenInRepoException(f"{file_path} does not contain a session {self.daq_version}")
        
        return file_path
