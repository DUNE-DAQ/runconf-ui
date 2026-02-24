'''
Wraps around runconf-ui, this "hides" most of the implementation details and handles the operations
required for file loading/openining 
'''
from pathlib import Path
from dataclasses import dataclass

from runconf_ui.exceptions import RunConfToolsRepoException
from runconf_ui.repo_manager import LocalRepoManager, RemoteRepoManager
from runconf_ui.system_configuration import SystemConfigReader
from runconf_ui.system_configuration.config_reader import AssembledGroup
from runconf_ui.utils import open_configuration
from runconf_ui.state_tree import Node, State, labelled

@dataclass
class RunconfContext:
    '''
    Basic context runconf-ui needs
    '''
    apparatus: str
    conf_directory: Path
    use_local: bool
    default_config: str | None = None
    base_url: str | None = None
    ops_url: str | None = None

AddressBookEntry= list[tuple[Node, State]]



class RunconfUI:
    '''
    Wrapper layer around RunConf-UI, this hides most of the operational details
    '''
    def __init__(self, context: RunconfContext):
        
        if context.use_local:
            self.repo_manager = LocalRepoManager(context.apparatus,
                                                 context.conf_directory)
        
        else:
            if any(d is None for d in (context.default_config, context.base_url, context.ops_url)):
                raise RunConfToolsRepoException("Error must set default config (blah.data.xml), base repo URL and operations repo URL to use runconftools")
            
            self.repo_manager = RemoteRepoManager(context.apparatus,
                                                  context.conf_directory,
                                                  context.default_config,
                                                  context.ops_url,
                                                  context.base_url)
            
        self.configuration = None
        self.system_config_reader: SystemConfigReader | None = None
        self.state_operations_tree = None
        self.address_book = None
        
    # Wrapper to make life easier
    def set_daq_version(self, version):
        self.repo_manager.set_daq_version(version)
        if version is not None:    
            self.system_config_reader = SystemConfigReader(self.repo_manager.get_runconf_ui_config_path())
        else:
            self.system_config_reader = None
            self.configuration = None 
            self.state_operations_tree = None
            self.address_book = None


    def select_config(self, config):
        if self.system_config_reader is None:
            raise RunConfToolsRepoException("No DAQ configuration setup, please select version first")

        self.configuration = open_configuration(self.repo_manager.select_config(config))
        
        self.state_operations_tree = self.system_config_reader.assemble_config(
            self.configuration,
            self.configuration.get_dals('Session')[0].id
        )

    def _make_id_map(self, group: list[AssembledGroup]):
        '''
        Gets a unique mapping from the group
        '''
        if group is None:
            return {}

        return_dict = {}
        for top_syst in group:
            return_dict[top_syst.label] = {}
            for syst in top_syst.systems:
                return_dict[syst] = [l.node.label for l in labelled(syst.root)]
        
        return return_dict