'''
Backend layer for runconf-ui
'''
from pathlib import Path

from runconf_ui.exceptions import RunConfToolsRepoException
from runconf_ui.repo_manager import LocalRepoManager, RemoteRepoManager
from runconf_ui.system_visibility import VisibilityConfigReader
from runconf_ui.utils import open_configuration


class RunconfUIBackend:
    def __init__(self, apparatus: str,
                 conf_directory: Path,
                 use_local: bool,
                 default_config: str | None = None,
                 base_url: str | None = None,
                 ops_url: str | None = None
                ):
        
        if use_local:
            self.repo_manager = LocalRepoManager(apparatus,
                                                 conf_directory)
        
        else:
            if not any(d is None for d in (default_config, base_url, ops_url)):
                raise RunConfToolsRepoException("Error must set default config, base URL and operations URL to use runconftools")
            
            self.repo_manager = RemoteRepoManager(apparatus,
                                                  conf_directory,
                                                  default_config,
                                                  ops_url,
                                                  base_url)
            
        self.configuration = None
        self.visbility_config_reader: VisibilityConfigReader | None = None
        self.state_operations_tree = None
        
    # Wrapper to make life easier
    def set_daq_version(self, version):
        self.repo_manager.set_daq_version(version)
        if version is not None:    
            self.visbility_config_reader = VisibilityConfigReader(self.repo_manager.get_runconf_ui_config_path())
        else:
            self.visbility_config_reader = None

        self.configuration = None 
        self.state_operations_tree = None
        
    def select_config(self, config):
        self.configuration = open_configuration(self.repo_manager.select_config(config))
        if self.visbility_config_reader is None:
            raise RunConfToolsRepoException("No DAQ configuration setup, please select version first")
        
        self.state_operations_tree = self.visbility_config_reader.generate_operations_tree(
            self.configuration,
            self.configuration.get_dals('Session')[0].id
        )
        
        