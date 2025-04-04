from runconf_ui.interfaces.controller.config_wrapper import ConfigurationWrapper
from runconf_ui.exceptions import CiderBadActionException

import runconf_ui.interfaces.actions.actions as ca
from runconf_ui.interfaces.workflows.get_set_session_attribute import (
    SetAttributeValueSessionAction,
    GetAttributeValueSessionAction,
)
from runconf_ui.interfaces.workflows.get_objects_in_session import (
    GetSegmentAppsListAction,
)

from typing import Dict, Sequence, Optional
from enum import IntEnum
from abc import ABC, abstractmethod
import traceback

import logging

"""
 Logic
    1. Input dict defined as

        System A:
            top_level_segement: str
            
            attributes:
              - id: strid: str
                class: str
                enabled_state: Any
                disabled_state: Any
                
                # If we want an additional button
                separate_system: bool
                label: str
              - ... 

            components:
              - id: str
                class: str
                enabled_state: bool
                disabled_state: bool
                
                # If we want an additional button
                separate_system: bool
                label: str
                - ...
    
        System B:
            ...
        
    2. Work out the state of each subsytem
        
"""


class SubsystemStatus(IntEnum):
    DISABLED = 0
    ENABLED = 1
    PARTIALLY_ENABLED = 2
    TOP_LEVEL_DISABLED = 3
    STATE_NOT_DEFINED = 4


class ItemExtractor(ABC):
    def __init__(
        self,
        configuration: ConfigurationWrapper | None,
        session_name: Optional[str] = None,
        disabled_dals=[],
    ):
        """
        Extracts the state of a subsystem. This is a base class for all extractors.


        :param configuration: Configuration object
        :type configuration: ConfigurationWrapper | None
        :param session_name: Name of session, defaults to None
        :type session_name: Optional[str], optional
        :param disabled_dals: List of disabled dals in configuration, defaults to []
        :type disabled_dals: list, optional
        """        

        # DAQ Configuration we're using
        self._configuration = configuration
        # The session name we're using
        self._session_name = session_name
        # The dal objects that are disabled
        self._disabled_dals = disabled_dals
        if configuration is None or session_name is None:
            return

    def set_config_session(
        self, configuration: ConfigurationWrapper, session_name: str
    ):
        # Set session + configuration within session
        self._configuration = configuration
        self._session_name = session_name

    def get_state(self, *args, **kwargs) -> SubsystemStatus:
        '''
        Wrapper around the get state function. This is used to catch exceptions
        '''
        try:
            return self._get_state(*args, **kwargs)
        except CiderBadActionException:
            return SubsystemStatus.STATE_NOT_DEFINED
        except Exception as e:
            logging.error(f"{traceback.format_exc()}")
            logging.error(f"Could not get state due to {e}")
            raise e

    @abstractmethod
    def _get_state(self, *args, **kwargs) -> SubsystemStatus:
        # Abstract method, use for getting state
        pass

    @abstractmethod
    def _set_state(self, state: SubsystemStatus, *args, **kwargs):
        # Abstract method, use for setting state
        pass

    def set_state(self, state: SubsystemStatus, *args, **kwargs):
        '''
        Wrapper around the set state function. This is used to catch exceptions
        '''
        try:
            self._set_state(state, *args, **kwargs)
        except CiderBadActionException:
            logging.debug("Could not set state")
            logging.debug(f"{traceback.format_exc()}")
        except Exception as e:
            logging.error(f"{traceback.format_exc()}")
            logging.error(f"Could not set state due to {e}")
            raise e

    def get_disabled_dals(self):
        return self._disabled_dals

    def set_disabled_dals(self, disabled_dals):
        self._disabled_dals = disabled_dals


class SubsystemExtractor(ItemExtractor):
    def __init__(
        self,
        configuration: ConfigurationWrapper | None,
        session_name: str,
        subsystem: dict,
        disabled_dals=[],
    ):
        """    
        Base class for extracting the state of a single subsystem.

        :param configuration: Configuration object
        :type configuration: ConfigurationWrapper | None
        :param session_name: Name of session
        :type session_name: str
        :param subsystem: Dictionary containing subsystem information
        :type subsystem: dict
        :param disabled_dals: List of disabled dals, defaults to []
        :type disabled_dals: list, optional
        
        
        Here subsystem dict is of the following form:
        {
            "id": str,                 # name of subsystem
            "class": str,              # DAL object class [i.e. "Segment", "Attribute"]
            "enabled_state": Any,      # enabled state of subsystem
            "disabled_state": Any,     # disabled state of subsystem
            'separate_system": bool,   # Does this require an additional button to the full system?
            "system_label": str,       # If it's a separate system, what is its name?
        }
        
        
        """        

        super().__init__(configuration, session_name, disabled_dals)

        # Subsystem information
        self._subsystem = subsystem
        self._session_dal = ca.GetDalObjectAction(self._configuration)(
            self._session_name, "Session"
        )

        # Attributes

        # DAL object class 
        self._system_class = subsystem["class"]
        # DAL object id
        self._system_id = subsystem["id"]

        # Enabled and disabled states i.e. what does it mean to be enabled/disabled
        self._enabled_state = subsystem.get("enabled_state", True)
        self._disabled_state = subsystem.get("disabled_state", False)

        # If this is a sub-system of the full system object, we need to know if it has a separate button
        self._is_system = subsystem.get("separate_system", False)
        # If it is a seoarate system, we need to know what the system name is
        self._system_name = subsystem.get("system_label", None)

        if self._is_system and self._system_name is None:
            raise CiderBadActionException(
                f"Subsystem {self._system_id} is a system but does not have a system name"
            )

    @property
    def is_system(self) -> bool:
        return self._is_system

    @is_system.setter
    def is_system(self, is_system: bool):
        self._is_system = is_system

    @property
    def system_name(self) -> str:
        return self._system_name

    @system_name.setter
    def system_name(self, name: str):
        self._system_name = name

    @property
    def system_id(self) -> str:
        return self._system_id

    @property
    def system_class(self) -> str:
        return self._system_class


class AttributeExtractor(SubsystemExtractor):
    def __init__(
        self,
        configuration: ConfigurationWrapper | None,
        session_name: str,
        subsystem: Dict,
        disabled_dals=[],
    ):
        """Extracts the state of a single ATTRIBUTE based subsystem. For example tpg_enabled/disabled

        :param configuration: Configuration object
        :param session_name: Name of session
        :param subsystem: Subsystem information dictionary
        :param disabled_dals: List of disabled dals, defaults to []
        
        For attributes the subsystem dict is of the following form:
        
        id: str,                 # name of attribute
        class: str,              # DAL object class with this component [i.e. "Segment", "Attribute"]
        segments: list,         # List of segments to search for this attribute
        enabled_state: Any,      # enabled state of subsystem
        disabled_state: Any,     # disabled state of subsystem
        separate_system: bool,   # Does this require an additional button to the full system?
        system_label: str,      # If it's a separate system, what is its name?

        
        """        
        
        super().__init__(configuration, session_name, subsystem, disabled_dals)

        # Get ALL segments in the system defined by a root segment
        self._segments = subsystem.get("segments", ["root-segment"])
        segment_dals = []

        # Get the dal object for each segment
        for s in self._segments:
            try:
                segment_dals.append(
                    ca.GetDalObjectAction(self._configuration)(s, "Segment")
                )
            except CiderBadActionException:
                logging.warning(
                    f"Could not get segment {s} for subsystem {self._system_id}"
                )
            except Exception as e:
                logging.error(f"{traceback.format_exc()}")
                logging.error(
                    f"Could not get segment {s} for subsystem {self._system_id} due to {e}"
                )
                logging.error(traceback.format_exc())
                raise e

        # Get DAL objects of the class specified in the subsystem dict in all objects in the segments 
        # below + including the root segment
        self._affected_objects = list(
            set(
                ca.GetAttributeAction(self._configuration)(a, "id")
                for t in segment_dals
                for a in GetSegmentAppsListAction(self._configuration)(t)
                if ca.GetClassNameAction(self._configuration)(a) == subsystem["class"]
            )
        )

    def _get_state(self) -> SubsystemStatus | None:
        '''
        Get state of the subsystem. Note that, since the attribtute may not be in a recognised enabled/disabled state
        this may return a partially enabled state. This is the case for example when the attribute is not set
        '''
        
        current_states = GetAttributeValueSessionAction(self._configuration)(
            self._session_dal,
            self._system_class,
            self._system_id,
            self._affected_objects,
        )

        if len(current_states) == 0:
            # No states found
            logging.debug(
                f"No states found for {self._system_id}, returning STATE_NOT_DEFINED")
            return SubsystemStatus.STATE_NOT_DEFINED

        # Check the first state, this is the state we will compare against
        state = current_states[0]

        if self.get_state_for_obj(state) == SubsystemStatus.STATE_NOT_DEFINED:
            # If the state is not enabled/disabled, we can't determine the state
            logging.debug(
                f"State for {self._system_id} is not defined, returning STATE_NOT_DEFINED")
            return SubsystemStatus.STATE_NOT_DEFINED

        # Check if all states are consistently enabled/disabled
        if all(
            [
                self.get_state_for_obj(a) == self.get_state_for_obj(state)
                for a in self._affected_objects
            ]
        ):
            return self.get_state_for_obj(state)

        return SubsystemStatus.PARTIALLY_ENABLED

    def get_state_for_obj(self, object_name: str) -> SubsystemStatus:
        '''
        Get state of a single object in the subsystem. This is used to check if the object is enabled/disabled
        '''
        try:
            object_dal = ca.GetDalObjectAction(self._configuration)(
                object_name, self._system_class
            )
            object_state = (
                ca.GetAttributeAction(self._configuration)(object_dal, self._system_id)
                and object_dal not in self._disabled_dals
            )

            if object_state == self._enabled_state:
                return SubsystemStatus.ENABLED

            return SubsystemStatus.DISABLED
            

        except Exception:
            raise CiderBadActionException(
                f"Could not get state for object {object_name} in subsystem {self._system_id}"
            )

    def _set_state(self, state: SubsystemStatus):
        if state == SubsystemStatus.PARTIALLY_ENABLED or state == SubsystemStatus.STATE_NOT_DEFINED:
            raise CiderBadActionException(
                f"Cannot set {state.name} for an attribute"
            )
    
        state_value = (
            self._enabled_state
            if state == SubsystemStatus.ENABLED
            else self._disabled_state
        )

        logging.info(
            f"Setting state of {self._session_dal} to {state_value} for {self._system_id}")

        SetAttributeValueSessionAction(self._configuration).action(
            self._session_dal,
            self._system_class,
            self._system_id,
            state_value,
            self._affected_objects,
        )

    def get_affected_object_names(self):
        # Get names of the dal objects affected by this attribute in the subsystem
        if self._affected_objects is None:
            return []

        return self._affected_objects

    def get_affected_object(self, obj_name):
        # Get single dal obj affected by this attribute in the subsystem
        if obj_name in self._affected_objects:
            return ca.GetDalObjectAction(self._configuration)(
                obj_name, self._system_class
            )
        return None

    def get_affected_object_dals(self):
        # Get dal objects affected by this attribute in the subsystem
        return [
            ca.GetDalObjectAction(self._configuration)(a, self._system_class)
            for a in self._affected_objects
        ]


class ComponentExtractor(SubsystemExtractor):
    '''
    Extracts the state of a single COMPONENT based subsystem. For example CRP enabled/disabled
    
    System info dict of the form
    
    id: str,                 # name of component
    class: str,              # DAL object class with this component [i.e. "Segment", "Attribute"]
    enabled_state: Any,      # enabled state of subsystem
    disabled_state: Any,     # disabled state of subsystem
    separate_system: bool,   # Does this require an additional button to the full system?
    system_label: str,      # If it's a separate system, what is its name?
    
    '''
    def _get_state(self) -> SubsystemStatus:
        '''
        Get state of the subsystem. This is always a boolean true/false
        '''
        
        subsystem_dal = self.get_dal()

        dal_disabled = ca.CheckIsDisabledAction(self._configuration)(
            subsystem_dal, self._session_name
        )

        logging.debug(
            f"Subsystem {self._system_id} is {'disabled' if dal_disabled else 'enabled'}"
        )

        return SubsystemStatus(
            not dal_disabled and subsystem_dal not in self._disabled_dals
        )

    def _set_state(self, state: SubsystemStatus):
        if state == SubsystemStatus.PARTIALLY_ENABLED:
            raise CiderBadActionException(
                "Cannot set partially enabled state for a component"
            )

        subsystem_dal = ca.GetDalObjectAction(self._configuration)(
            self._system_id, self._system_class
        )

        # Disable dal
        ca.DisableDalAction(self._configuration)(
            subsystem_dal, self._session_name, not state
        )
    
        # Update OKS object for dal and session
        ca.UpdateDalAction(self._configuration)(subsystem_dal)
        ca.UpdateDalAction(self._configuration)(self._session_dal)
        
        logging.debug(
            f"Subsystem {self._system_id} is {'disabled' if not state else 'enabled'}")

    def get_dal(self):
        return ca.GetDalObjectAction(self._configuration)(
            self._system_id, self._system_class
        )


class MultiItemExtractor(ItemExtractor):
    def __init__(
        self,
        configuration: ConfigurationWrapper | None,
        session_name: str | None = None,
        system: Dict | None = None,
        disabled_dals=[],
    ):
        '''
        :param configuration: Configuration object
        :param session_name: Name of session, defaults to None
        :param system: Dictionary containing system information, defaults to None
        :param disabled_dals: List of disabled dals, defaults to []
        
        Base class for extracting the state of multiple items. This is used to extract the state of a full subsystem
        '''
        super().__init__(configuration, session_name, disabled_dals)

        if self._configuration is not None and system is not None:
            self.read_system(system)

    def read_system(self, system: Optional[Dict]):
        if system is None or self._configuration is None or self._session_name is None:
            return False

        return True


class SystemExtractor(MultiItemExtractor):
    def __init__(
        self,
        configuration: Optional[ConfigurationWrapper],
        session: Optional[str],
        system_name: Optional[str],
        system: Optional[Dict],
        disabled_dals=[],
    ):
        '''
        :param configuration: Configuration object
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

        super().__init__(configuration, session, system, disabled_dals)

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
            AttributeExtractor(self._configuration, self._session_name, s)
            for s in system.get("attributes", [])
        ]
        
        logging.debug(f"Attributes: {[a.system_id for a in self._attributes]}")

        self._components = [
            ComponentExtractor(self._configuration, self._session_name, s)
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
        if self._session_name is None or self._configuration is None:
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


class DetectorExtractor(MultiItemExtractor):
    def __init__(
        self,
        configuration: ConfigurationWrapper,
        session: str | None,
        detector_config: Optional[Dict],
        disabled_dals=[],
    ):
        '''
        Extracts the states of ALL systems present in the detector config for a given top level system (i.e. trigger).
        :param configuration: Configuration object
        :param session: Name of session
        :param detector_config: Dictionary containing detector information
        :param disabled_dals: List of disabled dals, defaults to []
        
        Detector config is of the form
        
        "Detector System Name": {
            - label: str     # Name of the system for labelling widgets
            - panel_type:    # multi-system OR single system
            - Systems [
                {systsem_a},
                {system_b}, 
                ...
            ]
        }
        
        '''
        # Config file
        self._detector_config = {}
        # List of systems in the detector config
        self._system_extractors = []
        super().__init__(configuration, session, detector_config, disabled_dals)

    def read_system(self, detector_config: Dict):
        # Read system dict
        if not super().read_system(detector_config):
            return

        self._detector_config = detector_config
        self._system_extractors = []

        extracted_systems = detector_config.get("Systems", [])
        system_name = list(detector_config.keys())[0]
        
        logging.debug(f"Reading system {system_name}")

        for s in extracted_systems:
            try:
                system_name = list(s.keys())[0]

                system_info = list(s.values())[0]

                self._system_extractors.append(
                    SystemExtractor(
                        self._configuration,
                        self._session_name,
                        system_name,
                        system_info,
                    )
                )
            except CiderBadActionException:
                logging.debug(f"Could not extract system {system_name}")
            except Exception as e:
                logging.error(f"Could not extract system {system_name} due to {e}")
                logging.error(f"{traceback.format_exc()}")
                raise e

    def _set_state(self, state: SubsystemStatus, state_name: str):
        # Set state for a system in the detector config
        if state == SubsystemStatus.STATE_NOT_DEFINED:
            # Can't handle this
            return

        # Find correct system
        for system in self._system_extractors:
            # Check given system extractor contains the system name
            if state_name not in system.system_names:
                continue
            
            if state_name == system.system_name:
                for s in system.system_names:
                    system.set_state(state, s)
            else:
                system.set_state(state, state_name)

    def _get_state(self, state_name: str):
        for system in self._system_extractors:
            if state_name in system.system_names:
                return system.get_state(state_name)

        return SubsystemStatus.STATE_NOT_DEFINED

    @property
    def systems(self):
        return self._system_extractors

    def set_disabled_dals(self, disabled_dals):
        super().set_disabled_dals(disabled_dals)
        for system in self._system_extractors:
            system.set_disabled_dals(disabled_dals)

    def get_all_states(self):
        return_dict = {}
        # grab big dict
        for system in self._system_extractors:
            try:
                return_dict.update(system.get_all_states())
            except CiderBadActionException:
                logging.debug(f"Could not get all states for {system.system_name}")
                logging.debug(f"{traceback.format_exc()}")
            except Exception as e:
                logging.error(f"{traceback.format_exc()}")
                logging.error(
                    f"Could not get all states for {system.system_name} due to {e}"
                )
                raise e

        logging.debug(f"All states: {return_dict}")
        return return_dict

    @property
    def system_info(self):
        return self._detector_config
