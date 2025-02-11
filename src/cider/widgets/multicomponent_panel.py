from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.widgets.enable_disable_base import EnableDisablePanel
from cider.interfaces.workflows.get_set_session_attribute import (
    SetAttributeValueSessionAction,
    GetAttributeValueSessionAction,
)


import cider.interfaces.actions.actions as ca
from textual.visual import SupportsVisual
from textual.widgets import Button
from typing import Dict


class MultiComponentEnableDisablePanel(EnableDisablePanel):
    def __init__(
        self,
        configuration: ConfigurationWrapper | None,
        session_name: str | None,
        object_list: dict,
        content: str | SupportsVisual = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False
    ) -> None:
        super().__init__(
            configuration,
            session_name,
            content,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        """
        Object List:
        "CRP4" : {
            
            'subsystems': {
                "type": "component",
                "class": "Segment",
                "id": "crp4-segment",
                "enabled_val": True
            },
            'enabled': True
        }
            
        ,
        "CRP5" : {
            'subsystems': [{
                "type": "component",
                "class": "Segment",
                "id": "crp5-segment",
                "enabled": True
            }],
            'enabled': True
        }
        }
        """

        # Make a dict
        self._object_list = object_list

    def generate_button_list(self):
        if self._session_name is None or self._configuration is None:
            return {}

        session = ca.GetDalObjectAction(self._configuration)(
            self._session_name, "Session"
        )

        # Copy to ensure we don't modify the original
        output_dict = self._object_list.copy()

        for system_name, system_info in self._object_list.items():
            self._object_list[system_name]["enabled"] = self.check_initial_state(
                system_info
            )

            try:
                self.initialise_subsystem(session, system_info)
            except:
                # Can't find so don't add
                output_dict.pop(system_name)
                continue

        return output_dict

    def initialise_subsystem(self, session, system_info):

        for subsystem in system_info["subsystems"]:
            class_name = subsystem["class"]
            name = subsystem["id"]

            if system_info["enabled"]:
                state = subsystem["enabled_state"]
            else:
                state = subsystem["disabled_state"]

            # If we have an attribute object
            if subsystem["type"] == "attribute":
                affected_objects = subsystem["affected_objects"]
                SetAttributeValueSessionAction(self._configuration).action(
                    session, class_name, name, state, affected_objects
                )
            else:
                dal = ca.GetDalObjectAction(self._configuration)(name, class_name)
                ca.DisableDalAction(self._configuration).action(
                    dal, self._session_name, not state
                )

            ca.UpdateDalAction(self._configuration)(dal)

        ca.UpdateDalAction(self._configuration)(session)

    def check_initial_state(self, system_dict):
        """
        We want to be able to check the initial state of a subsytem, if all objects in it are in some
        basic initial state we can safely set enable/disable
        """
        try:
            attrs = [
                self.get_subsystem_disabled(subsystem)
                for subsystem in system_dict["subsystems"]
            ]
            
            if all(a == attrs[0] and attrs[0] for a in attrs) and attrs[0] is not None:            
                return not attrs[0]

        # Return some default value
            return system_dict["enabled"]

        except:
            return system_dict["enabled"]

    def get_subsystem_disabled(self, subsystem: Dict[str, str]) -> bool | None:
        class_name = subsystem["class"]
        name = subsystem["id"]

        if subsystem["type"] == "attribute":
            affected_objects = subsystem["affected_objects"]

            current_states = GetAttributeValueSessionAction(self._configuration)(
                self._session_name, class_name, name, affected_objects
            )
            if not all([c == current_states[0] for c in current_states]):
                return None

            if current_states[0] == subsystem["enabled_state"]:
                return False
            elif current_states[0] == subsystem["disabled_state"]:
                return True
            else:
                return None

        else:
            dal = ca.GetDalObjectAction(self._configuration)(name, class_name)            
            return (
                ca.CheckIsDisabledAction(self._configuration)(dal, self._session_name)
            )
            

    def _button_action(self, system_info, _):
        system_info["enabled"] = not system_info["enabled"]
        session_dal = ca.GetDalObjectAction(self._configuration)(
            self._session_name, "Session"
        )

        self.initialise_subsystem(session_dal, system_info)

    def check_is_disabled(self, button: str, _) -> bool:
        return not self._button_list.get(button, False)["enabled"]
