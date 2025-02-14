from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.exceptions import CiderBadActionException

import cider.interfaces.actions.actions as ca
from cider.utils.detector_subsystem import SubsystemInfo
from cider.exceptions import CiderBadActionException
from cider.interfaces.workflows.get_set_session_attribute import (
    SetAttributeValueSessionAction,
    GetAttributeValueSessionAction,
)
from typing import Dict, List, Any
from copy import deepcopy


class SystemInfoExtractor:
    def __init__(
        self, configuration: ConfigurationWrapper | None, session_name: str | None
    ):
        self._configuration = configuration
        self._session_name = session_name

    def set_config_session(
        self, configuration: ConfigurationWrapper, session_name: str
    ):
        self._configuration = configuration
        self._session_name = session_name

    def initialise_subsystem(self, system_dict: Dict) -> Dict:
        output_dict = deepcopy(system_dict)

        for system in system_dict.keys():
            try:
                subsystem_list = system_dict[system]["subsystems"]
                default_state = system_dict[system]["enabled"]
                output_dict[system]["enabled"] = self.check_full_subsystem_state(
                    subsystem_list, default_state
                )
            except CiderBadActionException:
                output_dict[system]["enabled"] = None
            except Exception as e:
                raise e

            if output_dict[system]["enabled"] is None:
                output_dict.pop(system)

        return output_dict

    def check_full_subsystem_state(
        self, subsystem_list: List[Dict], default_state
    ) -> bool | None:
        object_states = [
            self.check_single_object_state(subsystem, default_state)
            for subsystem in subsystem_list
        ]

        if all(
            s == object_states[0] and object_states[0] is not None
            for s in object_states
        ):
            return object_states[0]

        if object_states[0] == None:
            return None

        return default_state

    def check_single_object_state(self, system_obj: Dict, default_state) -> bool | None:
        subsystem_info = self._extract_subsystem_info(system_obj)

        if subsystem_info.type == "attribute":
            return self._check_attribute_state(subsystem_info, default_state)
        elif subsystem_info.type == "component":
            return self._check_component_state(subsystem_info)
        elif subsystem_info.type == "relationship":
            return self._check_relationship_state(subsystem_info)

        else:
            raise NotImplementedError(
                "Subsystems must be either an attribute or a component"
            )

    def _extract_subsystem_info(self, system_obj: Dict) -> SubsystemInfo:
        """Extract subsystem information from the system object."""
        return SubsystemInfo(
            type=system_obj["type"],
            class_name=system_obj["class"],
            id=system_obj["id"],
            enabled_state=system_obj["enabled_state"],
            disabled_state=system_obj["disabled_state"],
            affected_objects=system_obj.get("affected_objects", None),
            relationship_name=system_obj.get("relationship_name",None),
        )

    def _check_attribute_state(
        self, subsystem_info: SubsystemInfo, default_state
    ) -> bool | None:

        session_dal = ca.GetDalObjectAction(self._configuration)(
            self._session_name, "Session"
        )
        current_states = GetAttributeValueSessionAction(self._configuration)(
            session_dal,
            subsystem_info.class_name,
            subsystem_info.id,
            subsystem_info.affected_objects,
        )

        if len(current_states) == 0:
            return None

        is_enabled_list: List[bool | None] = []
        for s in current_states:
            if s == subsystem_info.enabled_state:
                is_enabled_list.append(True)
            elif s == subsystem_info.disabled_state:
                is_enabled_list.append(False)
            else:
                is_enabled_list.append(None)

        return (
            is_enabled_list[0]
            if all(
                s == is_enabled_list[0] and is_enabled_list[0] is not None
                for s in is_enabled_list
            )
            else default_state
        )
        
    def _check_relationship_state(self, subsystem_info: SubsystemInfo):
        # We're gonna need to get the dal
        
        subsystem_dal = ca.GetDalObjectAction(self._configuration)(
            subsystem_info.id, subsystem_info.class_name
        )
        
        
        
        if subsystem_info.enabled_state is None:
            enabled_dal = None
        else:
            enabled_dal = ca.GetDalObjectAction(self._configuration)(
                subsystem_info.enabled_state[0], subsystem_info.enabled_state[1]
            )

        if subsystem_info.disabled_state is None:
            disabled_dal = None
        else:
            disabled_dal = ca.GetDalObjectAction(self._configuration)(
                subsystem_info.disabled_state[0], subsystem_info.disabled_state[1]
            )

        if not isinstance(rel:= ca.GetAttributeAction(self._configuration)(subsystem_dal, subsystem_info.relationship_name), list):
            rel = [rel]

        # Check if it's a list
        # We're gonna just remove the enable and disabled states from the list
                
        if enabled_dal in rel:
            return True
        elif disabled_dal in rel:
            return False

        return None

            

    def _check_component_state(self, subsystem_info: SubsystemInfo) -> bool | None:
        subsystem_dal = ca.GetDalObjectAction(self._configuration)(
            subsystem_info.id, subsystem_info.class_name
        )

        return not ca.CheckIsDisabledAction(self._configuration)(
            subsystem_dal, self._session_name
        )

    def set_subsystem_states(self, system_dict: Dict):
        for system in system_dict.keys():
            subsystem_list = system_dict[system]["subsystems"]
            state = system_dict[system]["enabled"]
            self.set_full_subsystem_state(subsystem_list, state)

    def set_full_subsystem_state(self, subsystem_list: List[Dict], state: bool):
        for subsystem in subsystem_list:
            self.set_single_object_state(subsystem, state)

    def set_single_object_state(self, system_obj: Dict, state: bool):
        subsystem_info = self._extract_subsystem_info(system_obj)
        state_value = (
            subsystem_info.enabled_state if state else subsystem_info.disabled_state
        )
        session = ca.GetDalObjectAction(self._configuration)(
            self._session_name, "Session"
        )

        if subsystem_info.type == "attribute":
            self._set_attribute_state(subsystem_info, state_value, session)
        elif subsystem_info.type == "component":
            self._set_component_state(subsystem_info, state_value, session)
        elif subsystem_info.type == "relationship":
            self._set_relationship_state(subsystem_info, state_value)
        else:
            raise NotImplementedError(
                "Subsystems must be either an attribute or a component"
            )

    def _set_attribute_state(self, subsystem_info: SubsystemInfo, state: Any, session):
        SetAttributeValueSessionAction(self._configuration).action(
            session,
            subsystem_info.class_name,
            subsystem_info.id,
            state,
            subsystem_info.affected_objects,
        )
        
    def _set_relationship_state(self, subsystem_info: SubsystemInfo, state: Any):
        # basically the same as _set_attribute_state but we need to get the dal
        if state is None:
            state = None
        
        else:
            state = ca.GetDalObjectAction(self._configuration)(
                state[0], state[1]
            )

        subsystem_dal = ca.GetDalObjectAction(self._configuration)(
            subsystem_info.id, subsystem_info.class_name
        )
        
        # Check if it's a list
        if isinstance(rel_list:=ca.GetAttributeAction(self._configuration)(subsystem_dal, subsystem_info.relationship_name), list):
            # We're gonna just remove the enable and disabled states from the list
            if subsystem_info.enabled_state is not None:            
                enabled_dal = ca.GetDalObjectAction(self._configuration)(
                    subsystem_info.enabled_state[0], subsystem_info.enabled_state[1]
                )
                if enabled_dal in rel_list:
                    rel_list.remove(enabled_dal)

            else:
                enabled_dal = None
            
            if subsystem_info.disabled_state is not None:
                disabled_dal = ca.GetDalObjectAction(self._configuration)(
                    subsystem_info.disabled_state[0], subsystem_info.disabled_state[1]
                )
                if disabled_dal in rel_list:
                    rel_list.remove(disabled_dal)

            else:
                disabled_dal = None
            
            # Again massively inneficient but hey

            if state is not None:
                rel_list.append(state)
    
            state = rel_list
            
        # Now update 
        ca.ChangeAttributeAction(self._configuration)(
            subsystem_dal, subsystem_info.relationship_name, state
        )
        

        ca.UpdateDalAction(self._configuration)(subsystem_dal)
        

    def _set_component_state(self, subsystem_info: SubsystemInfo, state: Any, session):
        subsystem_dal = ca.GetDalObjectAction(self._configuration)(
            subsystem_info.id, subsystem_info.class_name
        )
        ca.DisableDalAction(self._configuration)(
            subsystem_dal, self._session_name, not state
        )
        ca.UpdateDalAction(self._configuration)(session)
