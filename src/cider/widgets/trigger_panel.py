from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.widgets.enable_disable_base import EnableDisablePanel
from cider.interfaces.workflows.get_set_session_attribute import (
    SetAttributeValueSessionAction,
    GetAttributeValueSessionAction,
)
import cider.interfaces.actions.actions as ca
from cider.utils.daq_conf_tree import TriggerTree

from textual.visual import SupportsVisual
from textual.widgets import Button

from rich.tree import Tree


class TriggerPanel(EnableDisablePanel):
    def __init__(
        self,
        configuration: ConfigurationWrapper | None,
        session_name: str | None,
        attribute_map: dict,
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
        """
        Attribute Map has form

        Trigger Label : {
            "attribute_name: str,
            "class_name": str,
            "object_names": List[str],
            "enabled_by_default": bool
        """

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

        self._attribute_map = attribute_map

    def generate_button_list(self):
        if self._session_name is None or self._configuration is None:
            return {}

        session = ca.GetDalObjectAction(self._configuration)(
            self._session_name, "Session"
        )
        
        output_map = self._attribute_map.copy()


        # This one is nice and simple!
        for trigger_label, trigger_info in self._attribute_map.items():

            class_name = trigger_info["class_name"]
            trigger_name = trigger_info["attribute_name"]
            object_names = trigger_info["object_names"]

            # Quick consistency check
            current_states = GetAttributeValueSessionAction(self._configuration)(
                session, class_name, trigger_name, object_names
            )

            enabled_state = trigger_info.get("enabled_state", True)
            disabled_state = trigger_info.get("disabled_state", True)

            if not current_states:
                output_map.pop(trigger_label)
                continue

            if (not all(s == current_states[0] for s in current_states)
                or current_states[0] not in {enabled_state, disabled_state}
            ):
                init_state = enabled_state
            else:
                init_state = current_states[0]

            # Set initial state of trigger
            trigger_info["enabled"] = init_state

            # This should be None
            object_names = trigger_info["object_names"]

            session = ca.GetDalObjectAction(self._configuration)(
                self._session_name, "Session"
            )

            SetAttributeValueSessionAction(self._configuration).action(
                session, class_name, trigger_name, trigger_info["enabled"], object_names
            )

        return output_map

    def check_is_disabled(self, button: str, _) -> bool:
        return not self._button_list.get(button, False)["enabled"]

    def _button_action(self, objs_affected, button_name):

        if objs_affected is None:
            return

        class_name = objs_affected["class_name"]
        object_names = objs_affected["object_names"]
        trigger_name = objs_affected["attribute_name"]

        # We want to flip this!
        if objs_affected["enabled"] == objs_affected.get("enabled_state", True):
            objs_affected["enabled"] = objs_affected.get("disabled_state", False)
        else:
            objs_affected["enabled"] = objs_affected.get("enabled_state", True)

        session = ca.GetDalObjectAction(self._configuration)(
            self._session_name, "Session"
        )

        SetAttributeValueSessionAction(self._configuration).action(
            session,
            class_name,
            trigger_name,
            objs_affected["enabled"],
            object_names,
        )
        
    def generate_display_tree(self):
        disabled_objects = super().generate_display_tree().disabled_objs
        return TriggerTree(self._configuration, self._session_name, self._button_list, disabled_objects)