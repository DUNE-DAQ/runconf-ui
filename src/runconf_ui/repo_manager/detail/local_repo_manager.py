from pathlib import Path

from runconf_ui.exceptions import DaqVersionException
from runconf_ui.repo_manager.repo_manager_interface import RepoManagerInterface
from runconf_ui.utils import get_configs_with_session


class LocalRepoManager(RepoManagerInterface[Path]):
    def __init__(self, apparatus: str, conf_directory: Path):
        super().__init__(apparatus, conf_directory)
        
        # Version is the "base" repo here
        self._available_versions = [conf_directory]
        self.set_daq_version(conf_directory)
                
    def get_available_daq_versions(self)->list[Path]:
        return self._available_versions
    
    def get_daq_sessions(self) -> list[Path]:
        if self.daq_version is None:
            return []
        
        return get_configs_with_session(self.daq_version)
    
    def select_config(self, config: Path):
        '''
        Bit of a dummy method
        '''
        
        if config in self.get_daq_sessions():
            return config
        
        # Check if we've just used the file name instead    
        c_full = next((p for p in self.get_daq_sessions() if p.name==config), None)
        
        if c_full is not None:
            return c_full
        
        raise DaqVersionException(f"Session {config} does not exist for {self.daq_version}")
        
    