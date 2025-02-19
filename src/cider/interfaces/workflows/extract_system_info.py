from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.exceptions import CiderBadActionException

import cider.interfaces.actions.actions as ca
from cider.utils.detector_subsystem import SubsystemInfo
from cider.interfaces.workflows.get_set_session_attribute import (
    SetAttributeValueSessionAction,
    GetAttributeValueSessionAction,
)
from typing import Dict, List, Any
from copy import deepcopy


class SystemInfoExtractor:
    """
    Object for checking and changing the state of a pre-defined multi-object system i.e. trigger/detector
    """

    def __init__(
        self, configuration: ConfigurationWrapper | None, session_name: str | None
    ):
        self._configuration = configuration
        self._session_name = session_name

    def set_config_session(
        self, configuration: ConfigurationWrapper, session_name: str
    ):
        """
        Change the session + config
        """
        self._configuration = configuration
        self._session_name = session_name

    def initialise_subsystem(self, system_dict: Dict) -> Dict:
        """
        Given a list of systems defined as
        [{Name: {
                subsystems: [{
                    type: "attribute" | "component",
                    class: "class_name",
                    id: "id",
                    enabled_state: "state",
                    disabled_state: "state",
                    affected_objects: ["obj1", "obj2"] # Optional and used only for attributes
                }]
            }
            enabled: "bool" # default state we want the object to be in if the configuration doesn't make sense
        },...]
        set up the interface and check state information.
        """
        output_dict = deepcopy(system_dict)

        # Loop over each system
        for system in system_dict.keys():
            try:
                # Grab system information
                subsystem_list = system_dict[system]["subsystems"]
                default_state = system_dict[system]["enabled"]

                # Set state to of the system to be the state of the subsystems
                output_dict[system]["enabled"] = self.check_full_subsystem_state(
                    subsystem_list, default_state
                )
            # If the action hits an error we set it to done
            except CiderBadActionException:
                output_dict[system]["enabled"] = None
            # Unhandled exceptions crash the app
            except Exception as e:
                raise e

            # If it's gone into error it likely doesn't exist and so we remove it
            if output_dict[system]["enabled"] is None:
                output_dict.pop(system)

        return output_dict

    def check_full_subsystem_state(
        self, subsystem_list: List[Dict], default_state
    ) -> bool | None:
        """
        Check the state of an entire system
        """

        # Get the state of all subsystems
        object_states = [
            self.check_single_object_state(subsystem, default_state)
            for subsystem in subsystem_list
        ]

        # Check for consistency, if all objects agree on the state return that
        if all(
            s == object_states[0] and object_states[0] is not None
            for s in object_states
        ):
            return object_states[0]

        # System has gone into error OR object doesn't exist
        if object_states[0] is None:
            return None

        # Return system's default state
        return default_state

    def check_single_object_state(self, system_obj: Dict, default_state) -> bool | None:
        """
        Check the state of a subsystem
        """
        # Get the subsystem information
        subsystem_info = self._extract_subsystem_info(system_obj)

        # Treat attribtues, components and relationships differently
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
            relationship_name=system_obj.get("relationship_name", None),
        )

    def _check_attribute_state(
        self, subsystem_info: SubsystemInfo, default_state
    ) -> bool | None:
        """
        Check the state of an attribute
        """

        # Get the session
        session_dal = ca.GetDalObjectAction(self._configuration)(
            self._session_name, "Session"
        )

        # Get the value of the attriubte for ALL affected objects
        current_states = GetAttributeValueSessionAction(self._configuration)(
            session_dal,
            subsystem_info.class_name,
            subsystem_info.id,
            subsystem_info.affected_objects,
        )

        # If none of these objects exist we return None so this is removed from the system
        if len(current_states) == 0:
            return None

        # Get state of all subsystems
        is_enabled_list: List[bool | None] = []

        # Need to check if the state is the same for all objects,
        # since enabled/disable may not = True/False we need to be careful
        for s in current_states:
            if s == subsystem_info.enabled_state:
                is_enabled_list.append(True)
            elif s == subsystem_info.disabled_state:
                is_enabled_list.append(False)
            else:
                is_enabled_list.append(None)

        # Return the state of the system if it's consistent across all objects
        # if an object is not well defined return None as the system cannot make sense
        # otherwise return the default state
        if all(
            s == is_enabled_list[0] and is_enabled_list[0] is not None
            for s in is_enabled_list
        ):
            return is_enabled_list[0]

        elif None in is_enabled_list:
            return None
        else:
            return default_state

    def _check_relationship_state(self, subsystem_info: SubsystemInfo):
        """
        For a button that switches between two states defined by a relationship
        """

        # Get the dal object for the subsystem
        subsystem_dal = ca.GetDalObjectAction(self._configuration)(
            subsystem_info.id, subsystem_info.class_name
        )

        # If enable/disable involves removing a relationship set it to done
        if subsystem_info.enabled_state is None:
            enabled_dal = None
        # Otherwise we can grab the dal object
        else:
            enabled_dal = ca.GetDalObjectAction(self._configuration)(
                subsystem_info.enabled_state[0], subsystem_info.enabled_state[1]
            )

        # And then do the same for the dsiabled state
        if subsystem_info.disabled_state is None:
            disabled_dal = None
        else:
            disabled_dal = ca.GetDalObjectAction(self._configuration)(
                subsystem_info.disabled_state[0], subsystem_info.disabled_state[1]
            )

        # Get the relationship, having it as a list makes it easier to handle
        if not isinstance(
            rel := ca.GetAttributeAction(self._configuration)(
                subsystem_dal, subsystem_info.relationship_name
            ),
            list,
        ):
            rel = [rel]

        # Check if it's a list
        # We're gonna just remove the enable and disabled states from the list

        # For now we do not handle the case where both are in the list
        if enabled_dal in rel:
            return True
        elif disabled_dal in rel:
            return False

        return None

    def _check_component_state(self, subsystem_info: SubsystemInfo) -> bool | None:
        """
        Check the state of a component. In this case components are just objects that can be enabled/disabled in the Session
        """

        # Grab dal
        subsystem_dal = ca.GetDalObjectAction(self._configuration)(
            subsystem_info.id, subsystem_info.class_name
        )

        # Simple check
        return not ca.CheckIsDisabledAction(self._configuration)(
            subsystem_dal, self._session_name
        )

    def set_subsystem_states(self, system_dict: Dict):
        """
        Set the state of all objects in a subsystem
        """
        for system in system_dict.keys():
            subsystem_list = system_dict[system]["subsystems"]
            state = system_dict[system]["enabled"]
            self.set_full_subsystem_state(subsystem_list, state)

    def set_full_subsystem_state(self, subsystem_list: List[Dict], state: bool):
        for subsystem in subsystem_list:
            """
            Set the state of a single subsystem
            """
            self.set_single_object_state(subsystem, state)

    def set_single_object_state(self, system_obj: Dict, state: bool):
        """
        Set the state of a single subsystem
        """

        # Info about the subsystem
        subsystem_info = self._extract_subsystem_info(system_obj)

        # We have the state info stored
        state_value = (
            subsystem_info.enabled_state if state else subsystem_info.disabled_state
        )

        # Grab session containing system
        session = ca.GetDalObjectAction(self._configuration)(
            self._session_name, "Session"
        )

        # Treat attribtues, components and relationships differently
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
        # Set the state of an attribute
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
            state = ca.GetDalObjectAction(self._configuration)(state[0], state[1])

        subsystem_dal = ca.GetDalObjectAction(self._configuration)(
            subsystem_info.id, subsystem_info.class_name
        )

        # Check if it's a list
        if isinstance(
            rel_list := ca.GetAttributeAction(self._configuration)(
                subsystem_dal, subsystem_info.relationship_name
            ),
            list,
        ):
            # We're gonna just remove the enable and disabled states from the list
            if subsystem_info.enabled_state is not None:
                enabled_dal = ca.GetDalObjectAction(self._configuration)(
                    subsystem_info.enabled_state[0], subsystem_info.enabled_state[1]
                )
                if enabled_dal in rel_list:
                    rel_list.remove(enabled_dal)

            else:
                enabled_dal = None

            # If the state is None that indicates we should remove the relationship
            if subsystem_info.disabled_state is not None:
                disabled_dal = ca.GetDalObjectAction(self._configuration)(
                    subsystem_info.disabled_state[0], subsystem_info.disabled_state[1]
                )
                if disabled_dal in rel_list:
                    rel_list.remove(disabled_dal)

            else:
                disabled_dal = None

            # Add state to relationship list
            if state is not None:
                rel_list.append(state)

            # Set state info
            state = rel_list

        # Now update
        ca.ChangeAttributeAction(self._configuration)(
            subsystem_dal, subsystem_info.relationship_name, state
        )

        # Update the dal
        ca.UpdateDalAction(self._configuration)(subsystem_dal)

    def _set_component_state(self, subsystem_info: SubsystemInfo, state: Any, session):
        """
        Set the state of the component in the session
        """

        # Grab dal for subsystem
        subsystem_dal = ca.GetDalObjectAction(self._configuration)(
            subsystem_info.id, subsystem_info.class_name
        )

        # Disable it
        ca.DisableDalAction(self._configuration)(
            subsystem_dal, self._session_name, not state
        )

        # Update
        ca.UpdateDalAction(self._configuration)(session)
