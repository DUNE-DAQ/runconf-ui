from runconf_ui.widgets.enable_disable_base import EnableDisablePanel
import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.utils.subsystem_status import SubsystemStatus
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)

from textual.visual import SupportsVisual
from typing import List
import logging

class SingleComponentEnableDisablePanel(EnableDisablePanel):
    """
    For enabling/disabling systems made of just a single component class
    """

    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        class_list: List[str],
        filters: List[dict] = [],
        tool_tip_var: str = "", 
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
            application_controller,
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
        self._filters = filters
        self._tool_tip_var = tool_tip_var
        self._tool_tip_list = []

    def generate_button_list(self):
        if (
            self._application_controller.session_name is None
            or self._application_controller.buffer_daq_config is None
        ):
            return {}
        
        buttons = []


        for class_ in self._class_list:
            logging.info(f"{class_}, {ca.GetDalsOfClassAction(self._application_controller.buffer_daq_config)(class_)}")
            buttons += ca.GetDalsOfClassAction(self._application_controller.buffer_daq_config)(class_)
                    
        logging.info(f"Buttons: {buttons}")
            
        if len(self._filters):
            buttons = self._filter_options(buttons)

        get_id = ca.GetAttributeAction(self._application_controller.buffer_daq_config)
        get_class = ca.GetClassNameAction(self._application_controller.buffer_daq_config)

        # Enabled first
        buttons = sorted(
            buttons,
            key=lambda x: self.check_button_state(get_id(x, "id"), get_class(x)),
            reverse=True,
        )

        # We want enabled first!
        return {get_id(b, "id"): get_class(b) for b in buttons}

    def _button_action(self, class_name, button_name):
        logging.info(f"Setting button state of {button_name} [ {class_name} ]")

        dal = ca.GetDalObjectAction(self._application_controller.buffer_daq_config)(
            button_name, class_name
        )
        session_dal = ca.GetDalObjectAction(
            self._application_controller.buffer_daq_config
        )(self._application_controller.session_name, "Session")

        if dal in ca.GetAttributeAction(self._application_controller.buffer_daq_config)(
            session_dal, "disabled"
        ):
            ca.DisableDalAction(self._application_controller.buffer_daq_config)(
                dal, self._application_controller.session_name, False
            )

        else:
            ca.DisableDalAction(self._application_controller.buffer_daq_config)(
                dal, self._application_controller.session_name, True
            )

        ca.UpdateDalAction(self._application_controller.buffer_daq_config)(session_dal)

    def check_button_state(
        self, button: str, information: str | List[str]
    ) -> SubsystemStatus:
        dal = ca.GetDalObjectAction(self._application_controller.buffer_daq_config)(
            button, information
        )
        return SubsystemStatus(
            not ca.CheckIsDisabledAction(self._application_controller.buffer_daq_config)(
                dal, self._application_controller.session_name
            )
        )

    def _filter_options(self, buttons):
        """
        Filter the options based on the filter list
        """
        filtered_buttons = []
        for button in buttons:
            for filter_ in self._filters:
                try:
                    if not ca.GetAttributeAction(
                        self._application_controller.buffer_daq_config
                    )(button, filter_["attribute"]) == filter_["value"]:
                        filtered_buttons.append(button)
                except Exception:
                    # If the attribute does not exist, we ignore it
                    filtered_buttons.append(button)
        
        return filtered_buttons