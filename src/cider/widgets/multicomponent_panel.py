from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.widgets.enable_disable_base import EnableDisablePanel

from textual.visual import SupportsVisual

from typing import Dict, Optional, List, NamedTuple, Any
from cider.interfaces.workflows.extract_system_info import SystemInfoExtractor


class MultiComponentEnableDisablePanel(EnableDisablePanel):
    def __init__(
        self,
        configuration: Optional[ConfigurationWrapper],
        session_name: Optional[str],
        object_list: Dict,
        content: str | SupportsVisual = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
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
        self._object_list = object_list
        self._extractor = SystemInfoExtractor(configuration, session_name)

    def generate_button_list(self) -> Dict:
        if self._session_name is None or self._configuration is None:
            return {}

        self._extractor.set_config_session(self._configuration, self._session_name)

        button_dict = self._extractor.initialise_subsystem(self._object_list)
        self._extractor.set_subsystem_states(button_dict)

        return button_dict

    def _button_action(self, objs_affected: Dict, button_name: str) -> None:
        self._button_list[button_name]["enabled"] = not self._button_list[button_name][
            "enabled"
        ]
        self._extractor.set_full_subsystem_state(
            objs_affected["subsystems"], self._button_list[button_name]["enabled"]
        )

    def check_is_disabled(self, button: str, _) -> bool:
        return not self._button_list.get(button, True)["enabled"]
