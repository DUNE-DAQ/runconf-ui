from runconf_ui.daq_config_interfaces.daq_config_file_io.daq_config_wrapper import DaqConfigurationWrapper
from runconf_ui.runconf_ui_configuration.detector_config_readers.extractor_interfaces import (MultiItemExtractor,
                                                                                           SubsystemExtractor)
from runconf_ui.runconf_ui_configuration.detector_config_readers.attribute_extractor import AttributeExtractor
from runconf_ui.runconf_ui_configuration.detector_config_readers.component_extractor import ComponentExtractor
from runconf_ui.utils.subsystem_status import SubsystemStatus
from runconf_ui.exceptions import CiderBadActionException

from typing import Dict, Sequence, Optional
import logging
import traceback




class SystemExtractor(MultiItemExtractor):
    def __init__(
        self,
        daq_configuration: Optional[DaqConfigurationWrapper],
        session: Optional[str],
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

        super().__init__(daq_configuration, session, system, disabled_dals)

    def read_system(self, system: Optional[Dict], system_name: Optional[str] = None):
        
        '''
        Read dictionary containing system information. This is used to extract the state of the system.
        '''
        # Just to allow this to be run at start up
        if not super().read_system(system):
            return

        self._system_name = (
            system_name if system_name is not None else self._system_name
        )

        logging.debug(f"Reading system {self._system_name}")

        self._attributes = [
            AttributeExtractor(self._daq_configuration, self._session_name, s)
            for s in system.get("attributes", [])
        ]
        
        logging.debug(f"Attributes: {[a.system_id for a in self._attributes]}")

        self._components = [
            ComponentExtractor(self._daq_configuration, self._session_name, s)
            for s in system.get("components", [])
        ]

        logging.debug(f"Components: {[c.system_id for c in self._components]}")
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

        logging.debug(f"System names: {self._system_names}")

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
        if system_name is not self.system_name:
            if self.get_state(self.system_name) == SubsystemStatus.DISABLED:
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

        if (
            all([s == states[0] for s in states])
            and states[0] is not SubsystemStatus.STATE_NOT_DEFINED
        ):
            logging.debug(
                f"All states are the same for {system_name}, returning {states[0].name}"
            )
            return states[0]


        logging.debug(
            f"States are not the same for {system_name}, returning PARTIALLY_ENABLED"
        )
        return SubsystemStatus.PARTIALLY_ENABLED

    def _set_state(self, state: SubsystemStatus, system_name: Optional[str]):
        # Basically if there are no non-system systems we assume this is a control for all subsystems!
        for s in self._attributes + self._components:
            if self._check_subsystem_cond(s, system_name):
                s.set_state(state)

    def get_all_states(self):
        '''
        Get the state of the system and any nested subsystems. 
        '''
        # Just to allow this to be run at start up
        if self._session_name is None or self._daq_configuration is None:
            return

        return_dict = {}
        return_dict[self._system_name] = self.get_state()

        # Grab the other systems
        for s in self._system_names:
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