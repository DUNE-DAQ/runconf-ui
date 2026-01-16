import logging

from textual.visual import SupportsVisual
from textual.widgets import Button

from runconf_ui.daq_config_interfaces.daq_tree_tools.daq_conf_tree import (
    ComponentLevelTree,
)
from runconf_ui.runconf_ui_configuration.object_extractors.detector_extractor import (
    DetectorExtractor,
)
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)
from runconf_ui.utils.subsystem_status import SubsystemStatus
from runconf_ui.widgets.enable_disable_base import EnableDisablePanel


class MultiComponentEnableDisablePanel(EnableDisablePanel):
    """
    For enabling/disabling systems made of many different things
    """

    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        object_list: dict = {},
        build_tree: bool = True,
        content: str | SupportsVisual = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:

        # Prevent the parent initializer from calling open_new_session before
        # we have set up attributes the subclass expects (like _extractor).
        # We use a small deferral flag that the overridden open_new_session
        # will honour during construction.
        self._defer_open = True

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

        # Now set up subclass-specific fields before running the real
        # open_new_session implementation.
        self._object_list = object_list
        self._disabled_items = []
        self._build_tree = build_tree

        logging.debug(f"Initializing MultiComponentEnableDisablePanel {id}...")
        self._extractor = DetectorExtractor(self._application_controller, object_list)
        logging.debug(f"Extractor initialized with {self._extractor.get_all_states()}")

        # Mark initialization complete and run the real open_new_session to
        # generate the button list now that _extractor exists.
        self._defer_open = False
        super().open_new_session()

        logging.debug("MultiComponentEnableDisablePanel initialized.")

    def generate_button_list(self) -> dict | None:
        if (
            self._application_controller.session_name is None
            or self._application_controller.buffer_daq_config is None
        ):
            return {}

        # Grabs state information for each button
        self._extractor.read_system(self._object_list)

        # Get states
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

    def get_tree(self)->ComponentLevelTree | None:
        if self._build_tree:
            return  ComponentLevelTree(
                self._application_controller,
                extractor=self._extractor,
            )
        return None 

    def on_mount(self):
        for button in self._button_list.keys():
            button_id = button.replace(" ", "~")
            try:
                button_widget = self.query_one(f"#{button_id}_button", Button)
            except Exception:
                continue

            button_widget.tooltip = self._extractor.get_tooltip(button)

    def get_tooltip(self, button_name: str) -> str:
        return self._extractor.get_tooltip(button_name)
