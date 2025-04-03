from runconf_ui.interfaces.controller.config_wrapper import ConfigurationWrapper
from runconf_ui.exceptions import CiderBadActionException

import runconf_ui.interfaces.actions.actions as ca
from runconf_ui.interfaces.workflows.get_set_session_attribute import (
    SetAttributeValueSessionAction,
    GetAttributeValueSessionAction,
)
from runconf_ui.interfaces.workflows.get_objects_in_session import GetSegmentAppsListAction

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

        self._configuration = configuration
        self._session_name = session_name
        self._disabled_dals = disabled_dals

        if configuration is None or session_name is None:
            return

    def set_config_session(
        self, configuration: ConfigurationWrapper, session_name: str
    ):
        self._configuration = configuration
        self._session_name = session_name

    @abstractmethod
    def _get_state(self, *args, **kwargs) -> SubsystemStatus:
        pass

    def get_state(self, *args, **kwargs) -> SubsystemStatus:
        try:
            return self._get_state(*args, **kwargs)
        except CiderBadActionException:
            return SubsystemStatus.STATE_NOT_DEFINED
        except Exception as e:
            logging.error(f"{traceback.format_exc()}")
            logging.error(f"Could not get state due to {e}")
            raise e

    @abstractmethod
    def _set_state(self, state: SubsystemStatus, *args, **kwargs):
        pass

    def set_state(self, state: SubsystemStatus, *args, **kwargs):
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
        super().__init__(configuration, session_name, disabled_dals)

        self._subsystem = subsystem
        self._session_dal = ca.GetDalObjectAction(self._configuration)(
            self._session_name, "Session"
        )

        # Attributes
        self._system_class = subsystem["class"]
        self._system_id = subsystem["id"]

        self._enabled_state = subsystem.get("enabled_state", True)
        self._disabled_state = subsystem.get("disabled_state", False)

        self._is_system = subsystem.get("separate_system", False)
        self._system_name = subsystem.get("system_label", None)

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

        super().__init__(configuration, session_name, subsystem, disabled_dals)

        self._segments = subsystem.get("segments", ["root-segment"])
        segment_dals = []

        for s in self._segments:
            try:
                segment_dals.append(
                    ca.GetDalObjectAction(self._configuration)(s, "Segment")
                )
            except CiderBadActionException:
                logging.debug(
                    f"Could not get segment {s} for subsystem {self._system_id}"
                )
            except Exception as e:
                logging.error(f"{traceback.format_exc()}")
                logging.error(
                    f"Could not get segment {s} for subsystem {self._system_id} due to {e}"
                )
                raise e

        self._affected_objects = list(
            set(
                ca.GetAttributeAction(self._configuration)(a, "id")
                for t in segment_dals
                for a in GetSegmentAppsListAction(self._configuration)(t)
                if ca.GetClassNameAction(self._configuration)(a) == subsystem["class"]
            )
        )

    def _get_state(self) -> SubsystemStatus | None:
        current_states = GetAttributeValueSessionAction(self._configuration)(
            self._session_dal,
            self._system_class,
            self._system_id,
            self._affected_objects,
        )

        if len(current_states) == 0:
            return SubsystemStatus.STATE_NOT_DEFINED

        state = current_states[0]

        if all(
            [
                self.get_state_for_obj(a) == SubsystemStatus.DISABLED
                for a in self._affected_objects
            ]
        ):
            return SubsystemStatus.DISABLED

        for s in current_states:
            if s != state:
                return SubsystemStatus.PARTIALLY_ENABLED

        return (
            SubsystemStatus.ENABLED
            if s == self._enabled_state
            else SubsystemStatus.DISABLED
        )

    def get_state_for_obj(self, object_name: str) -> SubsystemStatus:
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
            else:
                return SubsystemStatus.DISABLED

        except Exception:
            raise CiderBadActionException(
                f"Could not get state for object {object_name} in subsystem {self._system_id}"
            )

    def _set_state(self, state: SubsystemStatus):
        if state == SubsystemStatus.PARTIALLY_ENABLED:
            raise CiderBadActionException(
                "Cannot set partially enabled state for an attribute"
            )

        state_value = (
            self._enabled_state
            if state == SubsystemStatus.ENABLED
            else self._disabled_state
        )

        SetAttributeValueSessionAction(self._configuration).action(
            self._session_dal,
            self._system_class,
            self._system_id,
            state_value,
            self._affected_objects,
        )

    def get_affected_object_names(self):
        if self._affected_objects is None:
            return []

        return self._affected_objects

    def get_affected_object(self, obj_name):
        if obj_name in self._affected_objects:
            return ca.GetDalObjectAction(self._configuration)(
                obj_name, self._system_class
            )
        return None

    def get_affected_object_dals(self):
        return [
            ca.GetDalObjectAction(self._configuration)(a, self._system_class)
            for a in self._affected_objects
        ]


class ComponentExtractor(SubsystemExtractor):
    def _get_state(self) -> SubsystemStatus:
        subsystem_dal = self.get_dal()

        dal_disabled = ca.CheckIsDisabledAction(self._configuration)(
            subsystem_dal, self._session_name
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

        ca.DisableDalAction(self._configuration)(
            subsystem_dal, self._session_name, not state
        )

        ca.UpdateDalAction(self._configuration)(subsystem_dal)
        ca.UpdateDalAction(self._configuration)(self._session_dal)

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
        self._attributes = []
        self._components = []
        self._system_names = []

        self._system_name = system_name

        super().__init__(configuration, session, system, disabled_dals)

    def read_system(self, system: Optional[Dict], system_name: Optional[str] = None):
        # Just to allow this to be run at start up
        if not super().read_system(system):
            return

        self._system_name = (
            system_name if system_name is not None else self._system_name
        )

        self._attributes = [
            AttributeExtractor(self._configuration, self._session_name, s)
            for s in system.get("attributes", [])
        ]

        self._components = [
            ComponentExtractor(self._configuration, self._session_name, s)
            for s in system.get("components", [])
        ]

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
            self._system_names.append("root")

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

        # If the top level is disabled disable all lower level stuff
        if system_name is not self.system_name:
            if self.get_state(self.system_name) == SubsystemStatus.DISABLED:
                return SubsystemStatus.TOP_LEVEL_DISABLED

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
            return states[0]

        return SubsystemStatus.PARTIALLY_ENABLED

    def _set_state(self, state: SubsystemStatus, system_name: Optional[str]):

        # Basically if there are no non-system systems we assume this is a control for all subsystems!
        for s in self._attributes + self._components:
            if self._check_subsystem_cond(s, system_name):
                s.set_state(state)

    def get_all_states(self):
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
        return [
            s for s in self._attributes if self._check_subsystem_cond(s, system_name)
        ]

    def set_disabled_dals(self, disabled_dals):
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
        self._detector_config = {}
        self._system_extractors = []
        super().__init__(configuration, session, detector_config, disabled_dals)

    def read_system(self, detector_config: Dict):
        if not super().read_system(detector_config):
            return

        self._detector_config = detector_config
        self._system_extractors = []

        extracted_systems = detector_config.get("Systems", [])
        system_name = list(detector_config.keys())[0]

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
                logging.error(f"{traceback.format_exc()}")
                logging.error(f"Could not extract system {system_name} due to {e}")
                raise e

    def _set_state(self, state: SubsystemStatus, state_name: str):
        if state == SubsystemStatus.STATE_NOT_DEFINED:
            return

        for system in self._system_extractors:
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

        return return_dict

    @property
    def system_info(self):
        return self._detector_config
