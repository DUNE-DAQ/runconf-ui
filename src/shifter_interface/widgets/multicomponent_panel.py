from runconf_ui.interfaces.controller.config_wrapper import ConfigurationWrapper
from runconf_ui.widgets.enable_disable_base import EnableDisablePanel
from runconf_ui.interfaces.workflows.extract_system_info import (
    SubsystemStatus,
    DetectorExtractor,
)
from runconf_ui.utils.daq_conf_tree import ComponentLevelTree
from runconf_ui.interfaces.controller.application_controller import ShifterInterfaceState

from typing import Dict, Optional
from textual.visual import SupportsVisual
import logging


class MultiComponentEnableDisablePanel(EnableDisablePanel):
    """
    For enabling/disabling systems made of many different things
    """

    def __init__(
        self,
        app_controller: ShifterInterfaceState,
        object_list: Dict = {},
        content: str | SupportsVisual = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
        disabled: bool = False,
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

        self._object_list = object_list

        self._disabled_items = []

        self._extractor = DetectorExtractor(
            self._app_controller.dummy_oks_configuration,
            self._app_controller.session_name,
            object_list,
        )

    def generate_button_list(self) -> Dict | None:
        if (
            self._app_controller.session_name is None
            or self._app_controller.dummy_oks_configuration is None
        ):
            return {}

        # Set up information extractor
        self._extractor.set_config_session(
            self._app_controller.dummy_oks_configuration,
            self._app_controller.session_name,
        )

        # Grabs state information for each button
        self._extractor.read_system(self._object_list)

        # Makes sure that the button states are set correctly and consistent

        return self._extractor.get_all_states()

    def _button_action(self, _, button_name: str) -> None:

        current_state = self._extractor.get_state(button_name)
        if current_state == SubsystemStatus.STATE_NOT_DEFINED:
            logging.error(f"State not defined for {button_name}")
            return

        # Specific handlers for these cases
        if current_state == SubsystemStatus.PARTIALLY_ENABLED:
            current_state = SubsystemStatus.ENABLED

        if current_state == SubsystemStatus.TOP_LEVEL_DISABLED:
            current_state = SubsystemStatus.DISABLED

        desired_state = SubsystemStatus(not bool(current_state))

        self._extractor.set_state(desired_state, button_name)

    def update_disabled(self, disabled_states):
        self._disabled_items = disabled_states
        self._extractor.set_disabled_dals(disabled_states)

    def check_button_state(self, button: str, _) -> SubsystemStatus:
        return self._extractor.get_state(button)

    def get_tree(self):

        tree = ComponentLevelTree(
            self._app_controller,
            extractor=self._extractor,
        )
        return tree
