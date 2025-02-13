from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.widgets.enable_disable_base import EnableDisablePanel


import cider.interfaces.actions.actions as ca
from cider.interfaces.workflows.get_objects_in_session import GetObjectsInSessionAction
from textual.visual import SupportsVisual
from textual.widgets import Button
from typing import List, Dict


class SingleComponentEnableDisablePanel(EnableDisablePanel):

    def __init__(
        self,
        configuration: ConfigurationWrapper | None,
        session_name: str | None,
        class_list: List[str],
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

        # Make a dict
        self._class_list = class_list

    def generate_button_list(self):
        if self._session_name is None or self._configuration is None:
            return {}

        session = ca.GetDalObjectAction(self._configuration)(
            self._session_name, "Session"
        )

        buttons = []

        for class_ in self._class_list:
            buttons += GetObjectsInSessionAction(self._configuration)(session, class_)

        return {
            ca.GetAttributeAction(self._configuration)(b, "id"): ca.GetClassNameAction(
                self._configuration
            )(b)
            for b in buttons
        }

    def _button_action(self, class_name, button_name):

        dal = ca.GetDalObjectAction(self._configuration)(button_name, class_name)
        session_dal = ca.GetDalObjectAction(self._configuration)(
            self._session_name, "Session"
        )

        if dal in ca.GetAttributeAction(self._configuration)(session_dal, "disabled"):
            ca.DisableDalAction(self._configuration)(dal, self._session_name, False)

        else:
            ca.DisableDalAction(self._configuration)(dal, self._session_name, True)

        ca.UpdateDalAction(self._configuration)(session_dal)

    def check_is_disabled(self, button: str, information: str | List[str]) -> bool:
        dal = ca.GetDalObjectAction(self._configuration)(button, information)
        return ca.CheckIsDisabledAction(self._configuration)(dal, self._session_name)
