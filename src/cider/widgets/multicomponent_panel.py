from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.widgets.enable_disable_base import EnableDisablePanel
from cider.interfaces.workflows.extract_system_info import (
    SubsystemStatus,
    DetectorExtractor,
)
from cider.utils.daq_conf_tree import ComponentLevelTree

from typing import Dict, Optional
from textual.visual import SupportsVisual


class MultiComponentEnableDisablePanel(EnableDisablePanel):
    """
    For enabling/disabling systems made of many different things
    """

    def __init__(
        self,
        configuration: Optional[ConfigurationWrapper],
        session_name: Optional[str] = "",
        object_list: Dict = {},
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

        self._disabled_items = []

        self._extractor = DetectorExtractor(configuration, session_name, object_list)

    def generate_button_list(self) -> Dict | None:
        if self._session_name is None or self._configuration is None:
            return {}

        # Set up information extractor
        self._extractor.set_config_session(self._configuration, self._session_name)

        # Grabs state information for each button
        self._extractor.read_system(self._object_list)

        # Makes sure that the button states are set correctly and consistent

        return self._extractor.get_all_states()

    def _button_action(self, _, button_name: str) -> None:

        current_state = self._extractor.get_state(button_name)

        # Specific handlers for these cases
        if current_state == SubsystemStatus.PARTIALLY_ENABLED:
            current_state = SubsystemStatus.DISABLED

        if current_state == SubsystemStatus.TOP_LEVEL_DISABLED:
            current_state = SubsystemStatus.DISABLED

        desired_state = SubsystemStatus(not bool(current_state))

        self._extractor.set_state(desired_state, button_name)

    def update_disabled(self, disabled_states):
        self._disabled_items = disabled_states
        self._extractor.set_disabled_dals(disabled_states)

    def check_button_state(self, button: str, _) -> SubsystemStatus:
        return SubsystemStatus(self._extractor.get_state(button))

    def get_tree(self):

        tree = ComponentLevelTree(
            configuration=self._configuration,
            session=self._session_name,
            extractor=self._extractor,
        )
        return tree
