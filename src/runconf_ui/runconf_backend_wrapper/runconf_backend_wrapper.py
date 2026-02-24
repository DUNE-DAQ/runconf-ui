'''
Backend layer for runconf-ui
'''
from pathlib import Path
from dataclasses import dataclass

from runconf_ui.exceptions import RunConfToolsRepoException
from runconf_ui.repo_manager import LocalRepoManager, RemoteRepoManager
from runconf_ui.system_configuration import SystemConfigReader
from runconf_ui.system_configuration.config_reader import AssembledGroup
from runconf_ui.utils import open_configuration
from runconf_ui.state_tree import labelled, Node, State

@dataclass
class RunconfContext:
    apparatus: str
    conf_directory: Path
    use_local: bool
    default_config: str | None = None
    base_url: str | None = None
    ops_url: str | None = None

AddressBookEntry= list[tuple[Node, State]]

class RunconfBackendWrapper:
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
        
        self.generate_address_book()
    
    
    def generate_address_book(self):
        '''
        Build the nested address book
        |panel -> buttons -> nodes|
        
        '''
        if self.state_operations_tree is None:
            self.address_book = {'disableable': [], 'adjustable': []}
        
        else:
            self.address_book =  {'disableable' : self._generate_address_book(self.state_operations_tree.disableable),
                                  'adjustable'  : self._generate_address_book(self.state_operations_tree.adjustable)}
        
        
    def _generate_address_book(self, assembled_groups: list[AssembledGroup])->dict[str, AddressBookEntry]:
        addresses = {}
        for group in assembled_groups:
            addresses[group.label] = [(n.node, n.state) for system in group.systems for n in labelled(system.root)]
        
        return addresses