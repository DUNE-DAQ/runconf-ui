from runconf_ui.daq_config_interfaces.daq_config_file_io.daq_config_wrapper import DaqConfigurationWrapper
from runconf_ui.runconf_ui_configuration.detector_config_readers.extractor_interfaces import (MultiItemExtractor,
                                                                                           SubsystemExtractor)
from runconf_ui.runconf_ui_configuration.detector_config_readers.attribute_extractor import AttributeExtractor
from runconf_ui.runconf_ui_configuration.detector_config_readers.component_extractor import ComponentExtractor
from runconf_ui.runconf_ui_configuration.detector_config_readers.relationship_extractor import RelationshipExtractor
from runconf_ui.utils.subsystem_status import SubsystemStatus
from runconf_ui.exceptions import CiderBadActionException
import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)


from typing import Dict, Sequence, Optional
import logging
import traceback

class SystemExtractor(MultiItemExtractor):
    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        system_name: Optional[str],
        system: Optional[Dict],
        disabled_dals=[],
    ):
        '''
        :param daq_configuration: daq_configuration object
        :param session: Name of session
        :param system_name: Name of system
        :param system: Dictionary containing system information
        :param disabled_dals: List of disabled dals, defaults to []
        
        System is of form
        
        "System_Name": {
            subsystem_dependent: bool, # If all subsystems are disabled, disable this system
            attributes: [ <list of attribute subsystems> ],
            components: [ <list of component subsystems> ]
        }
        
        
        '''
        
        # List of attributes to enable/disable in the system
        self._attributes = []
        # List of componets to enable/disable in the system
        self._components = []
        # If the system contains multiple systems, we need to know what they are for example TPC may contain multiple CRPs
        self._system_names = []

        # The system name for the full sysystem
        self._system_name = system_name
        self._display_full_system = True

        super().__init__(application_controller, system, disabled_dals)

    def read_system(self, system: Dict, system_name: Optional[str] = None):
        
        '''
        Read dictionary containing system information. This is used to extract the state of the system.
        '''
        # Just to allow this to be run at start up
        if not super().read_system(system):
            logging.error(f"System with name {system_name} is not valid, cannot read system.")
            return
        
        self._system_name = (
            system_name if system_name is not None else self._system_name
        )

        logging.debug(f"Reading system {self._system_name}")

        self._attributes = [
            AttributeExtractor(self._application_controller, s)
            for s in system.get("attributes", [])
        ]
        
        self._attributes.extend(RelationshipExtractor(self._application_controller, s)
            for s in system.get("relationships", []))
        
        self.extract_components(system)

        self._system_names = list(
            set(
                [
                    s.system_name
                    for s in self._attributes + self._components
                    if s.is_system
                ]
            )
        )
        
        
        if self._system_name is not None:
            self._system_names.append(self._system_name)
        else:
            # If the system name is not defined, we assume this is the root system
            self._system_names.append("root")

        self._subsystem_dependent = system.get("subsystem_dependent", False)
        self._display_full_system = system.get("display_full_system", True)

        logging.debug(f"System names: {self._system_names}")

    def extract_components(self, system: Dict):
        self._components = []
        for s in system.get("components", []):
            if s.get('each_component_separate', False):
                # If the component is not a separate component, we can just add it as a subsystem
                self.__extract_multi_comp(s)
            # If the component is a separate component, we need to which contain the ID as the substring + are the right class
            else:
                self.__add_component(s)

    def __extract_multi_comp(self, sub_syst: Dict):
        comp_names = self.find_components_with_wildcard(sub_syst['id'], sub_syst['class'])
        for comp in comp_names:
            s_copy = sub_syst.copy()            
            # Swap the id around to ensure uniqueness
            s_copy['id'] = comp

            # If the component is not a separate system, we need to set the system label and separate_system
            # this gives us buttons for each component in the system
            if not s_copy.get('separate_system', False):     
                s_copy['system_label'] = comp
                s_copy['separate_system'] = True

            self.__add_component(s_copy)


    def __add_component(self, system: Dict):
        ext = ComponentExtractor(self._application_controller, system)    
        if not ext.is_filtered():
            self._components.append(ext)


    @property
    def system_names(self) -> Sequence[str]:
        return self._system_names

    @property
    def system_name(self) -> str | None:
        return self._system_name

    def _check_subsystem_cond(
        self, subsystem: SubsystemExtractor, system_name: str | None
    ):
        if system_name is None or system_name == self._system_name:
            return True
        else:
            return subsystem.system_name == system_name

    def _get_state(self, system_name: Optional[str] = None) -> SubsystemStatus | None:
        '''
        Get state of the system. This is used to check if the system is enabled/disabled
        :param system_name: Name of the (sub)system to check, defaults to None
        '''

        # If the top level is disabled disable all lower level stuff
        if system_name != self._system_name:
            if self.get_state(self.system_name) in [SubsystemStatus.DISABLED, SubsystemStatus.TOP_LEVEL_DISABLED]\
            and not self._subsystem_dependent:
                return SubsystemStatus.TOP_LEVEL_DISABLED

        # Get the state of all subsystems in the system        
        states = [
            s.get_state()
            for s in self._attributes + self._components
            if self._check_subsystem_cond(s, system_name)
            and s.get_state() is not SubsystemStatus.STATE_NOT_DEFINED
        ]

        if len(states) == 0:
            logging.debug(f"No states found for {system_name}")
            return SubsystemStatus.STATE_NOT_DEFINED

        # If we depend on subsystem behaviour
        if system_name in [None, self._system_name] and self._subsystem_dependent: 
            # If the system is not defined, we assume this is the root system
            state = self._get_subsystem_state()
            if state != SubsystemStatus.STATE_NOT_DEFINED:
                return state

        # Otherwise we check the states of the system itself
        if (
            all([s == states[0] for s in states])
            and states[0] is not SubsystemStatus.STATE_NOT_DEFINED
        ):
            return states[0]


        logging.debug(
            f"States are not the same for {system_name}, returning PARTIALLY_ENABLED"
        )
        return SubsystemStatus.PARTIALLY_ENABLED

    def _get_subsystem_state(self) -> SubsystemStatus:
        subsyst_states = [
            s.get_state()
            for s in self._attributes + self._components
            if s.get_state() is not SubsystemStatus.STATE_NOT_DEFINED
            and s.is_system
        ]
    
        if not len(subsyst_states):
            return SubsystemStatus.STATE_NOT_DEFINED

        if all([s == subsyst_states[0] for s in subsyst_states]):
            return subsyst_states[0]            

        else:
            return SubsystemStatus.PARTIALLY_ENABLED
        

    def _set_state(self, state: SubsystemStatus, system_name: Optional[str]):
        # Basically if there are no non-system systems we assume this is a control for all subsystems!
        if self._subsystem_dependent:
            self._set_full_system_state(state, system_name)

        for s in self._attributes + self._components: 
            if self._check_subsystem_cond(s, system_name):
                s.set_state(state)



    def _set_full_system_state(self, state: SubsystemStatus, system_name: str | None):
        '''
        Set state of non-subsystem comps
        
        Logic is as follows:
            1. If the system is not defined, we assume this is the root system and ignore
            2. We look at the state of all subsystems that AREN'T the root system or the one we're about to set
            3. If everything else is different to the state we're about to set, we set the state to PARTIALLY_ENABLED
            4. If everything else is the same, we set the state to the state we're about to set
            
        This means we can enable/disable global components at will. This is painful logic but it works.
        
        '''
        if system_name is None:
            return
        
        subsystem_states = [
            s.get_state()
            for s in self._attributes + self._components
            if s.get_state() is not SubsystemStatus.STATE_NOT_DEFINED
            and s.is_system
            and s.system_name != system_name
        ]
        
        if all([s==subsystem_states[0] for s in subsystem_states]) and subsystem_states[0]==state:
            ...
        else:
            state = SubsystemStatus.ENABLED

        for st in self._attributes + self._components:
            if not st.is_system: 
                st.set_state(state)
        
        if state == SubsystemStatus.PARTIALLY_ENABLED:
            return
        
        else:
            for s in self._attributes + self._components:
                if not s.is_system: 
                    s.set_state(state)  

    def get_all_states(self):
        '''
        Get the state of the system and any nested subsystems. 
        '''
        # Just to allow this to be run at start up
        if self._application_controller.session_name is None or self._application_controller.buffer_daq_config is None:
            return

        return_dict = {}
        
        if self._display_full_system:
            return_dict[self._system_name] = self.get_state()

        # Grab the other systems
        for s in sorted(self._system_names):
            if s in [None, self._system_name]:
                continue
        
            try:
                state = self.get_state(s)
                if state is not None:
                    return_dict.update({s: self.get_state(s)})

            except CiderBadActionException:
                logging.debug(f"Could not get state for {s} in {self.system_name}")
            except Exception as e:
                logging.error(f"{traceback.format_exc()}")
                logging.error(f"Could not get state for {s} due to {e}")

        return return_dict

    def get_components(self, system_name: Optional[str] = None):
        return [
            s for s in self._components if self._check_subsystem_cond(s, system_name)
        ]

    def get_attributes(self, system_name: Optional[str] = None):
        # Get list of attributes in system
        return [
            s for s in self._attributes if self._check_subsystem_cond(s, system_name)
        ]

    def set_disabled_dals(self, disabled_dals):
        # Set the disabled dals for the system and all subsystems
        super().set_disabled_dals(disabled_dals)
        for s in self._attributes + self._components:
            s.set_disabled_dals(disabled_dals)
            
    def find_components_with_wildcard(self, wildcard: str, class_name: str):
        """
        Find components with a wildcard in the system.
        :param wildcard: Wildcard to search for
        :param system_name: Name of the system to search in, defaults to None
        :return: List of components that match the wildcard
        """
        dals = ca.GetDalsOfClassAction(self._application_controller.buffer_daq_config)(class_name)
        if not dals:
            return []
        
        return [ca.GetAttributeAction(self._application_controller.buffer_daq_config)(d, "id") for d in dals
                if wildcard in ca.GetAttributeAction(self._application_controller.buffer_daq_config)(d, "id")]
        
