from runconf_ui.interfaces.controller.config_wrapper import ConfigurationWrapper
from runconf_ui.widgets.enable_disable_base import EnableDisablePanel
from runconf_ui.interfaces.workflows.get_objects_in_session import GetObjectsInSessionAction
import runconf_ui.interfaces.actions.actions as ca
from runconf_ui.interfaces.workflows.extract_system_info import SubsystemStatus
from runconf_ui.interfaces.controller.application_controller import ShifterInterfaceState

from textual.visual import SupportsVisual
from typing import List


class SingleComponentEnableDisablePanel(EnableDisablePanel):
    """
    For enabling/disabling systems made of just a single component class
    """

    def __init__(
        self,
        app_controller: ShifterInterfaceState,
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
            app_controller,
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
        if (
            self._app_controller.session_name is None
            or self._app_controller.dummy_oks_configuration is None
        ):
            return {}

        session = ca.GetDalObjectAction(self._app_controller.dummy_oks_configuration)(
            self._app_controller.session_name, "Session"
        )

        buttons = []

        for class_ in self._class_list:
            buttons += GetObjectsInSessionAction(
                self._app_controller.dummy_oks_configuration
            )(session, class_)

        get_id = ca.GetAttributeAction(self._app_controller.dummy_oks_configuration)
        get_class = ca.GetClassNameAction(self._app_controller.dummy_oks_configuration)

        # Enabled first
        buttons = sorted(
            buttons,
            key=lambda x: self.check_button_state(get_id(x, "id"), get_class(x)),
            reverse=True,
        )

        # We want enabled first!
        return {get_id(b, "id"): get_class(b) for b in buttons}

    def _button_action(self, class_name, button_name):

        dal = ca.GetDalObjectAction(self._app_controller.dummy_oks_configuration)(
            button_name, class_name
        )
        session_dal = ca.GetDalObjectAction(
            self._app_controller.dummy_oks_configuration
        )(self._app_controller.session_name, "Session")

        if dal in ca.GetAttributeAction(self._app_controller.dummy_oks_configuration)(
            session_dal, "disabled"
        ):
            ca.DisableDalAction(self._app_controller.dummy_oks_configuration)(
                dal, self._app_controller.session_name, False
            )

        else:
            ca.DisableDalAction(self._app_controller.dummy_oks_configuration)(
                dal, self._app_controller.session_name, True
            )

        ca.UpdateDalAction(self._app_controller.dummy_oks_configuration)(session_dal)

    def check_button_state(
        self, button: str, information: str | List[str]
    ) -> SubsystemStatus:
        dal = ca.GetDalObjectAction(self._app_controller.dummy_oks_configuration)(
            button, information
        )
        return SubsystemStatus(
            not ca.CheckIsDisabledAction(self._app_controller.dummy_oks_configuration)(
                dal, self._app_controller.session_name
            )
        )
