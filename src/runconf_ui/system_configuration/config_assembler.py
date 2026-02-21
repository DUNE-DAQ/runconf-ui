'''
Builds state operations from a YAML configuration
'''
from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.system_configuration.system_builders import create_system_builder

from .config_dataclasses import AdjustableGroupData, DisableableGroupData


class ConfigAssembler:
    '''
    Turns a YAML config skeleton into a series of state operations
    '''
    def __init__(self, configuration: Configuration, session: DalBase):
        self.configuration = configuration
        self.session = session
        
    def assemble_config(self, skeleton: dict[str, DisableableGroupData | AdjustableGroupData], builder_type: str) -> list:
        '''
        Builds a nice tree containing our system information
        '''
        system_info = []
        system_builder = create_system_builder(builder_type, self.configuration, self.session)
        
        for group_name, group_config in skeleton.items():            
                group_info = {"id": group_name,
                    "label": group_config.label or group_name,
                    "view_panel": getattr(group_config, 'view_panel', None),
                    "systems": [
                        {'system': system_builder.build(s),
                        'display_full_system': getattr(s, 'display_full_system', False)}
                        for systems_list in group_config.systems.values()
                        for s in systems_list
                    ]
                    }
                

                system_info.append(group_info)

        return system_info

