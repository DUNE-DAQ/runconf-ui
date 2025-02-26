from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
import cider.interfaces.actions.actions as ca
from cider.interfaces.workflows.extract_system_info import SubsystemStatus

from textual.visual import SupportsVisual
from textual.widgets import Static, Button
from textual.containers import ScrollableContainer
from textual.message import Message
import logging


class EnableDisablePanel(Static):
    """
    Base class for all of the enable/disable button panel
    """

    def __init__(
        self,
        configuration: ConfigurationWrapper | None,
        session_name: str | None,
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
        super().__init__(
            content,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

        self._configuration = None

        self.open_new_session(configuration, session_name)

    @property
    def configuration(self) -> ConfigurationWrapper | None:
        return self._configuration

    @property
    def session_name(self) -> str | None:
        return self._session_name

    def open_new_session(
        self, configuration: ConfigurationWrapper | None, session_name: str | None
    ):
        if self._configuration is not None:
            ca.UnloadConfigurationAction(self._configuration)()

        self._session_name = session_name
        self._configuration = configuration

        self._button_list = self.generate_button_list()

        # Need default initial states
        self._default_states = {
            k: self.check_button_state(k, b) for k, b in self._button_list.items()
        }

        # Update everything else!
        self.post_message(self.Changed(self._configuration, self._session_name))

    def check_button_state(self, *args, **kwargs) -> bool:
        raise NotImplementedError("Check is disabled not implemented for class")

    def compose(self):
        with ScrollableContainer(id="buttons_panel"):
            for button, information in self._button_list.items():

                button_status = self.check_button_state(button, information)

                if button_status == SubsystemStatus.ENABLED:
                    name_str = f"{button} (Enabled)"
                    classes = (
                        "detector_subsystem_button detector_subsystem_button_enabled"
                    )
                elif button_status == SubsystemStatus.PARTIALLY_ENABLED:
                    name_str = f"{button} (Partially Enabled)"
                    classes = (
                        "detector_subsystem_button detector_subsystem_button_partial"
                    )
                else:
                    name_str = f"{button} (Disabled)"
                    classes = (
                        "detector_subsystem_button detector_subsystem_button_disabled"
                    )

                id_name = button.replace(" ", "_")

                yield Button(name_str, id=f"{id_name}_button", classes=classes)

    def on_button_pressed(self, event: Button.Pressed):
        button_name = event.button.id.replace("_button", "")

        button_name = button_name.replace("_", " ")
        objs_affected = self._button_list.get(button_name, None)

        if objs_affected is None:
            return

        self._button_action(objs_affected, button_name)
        self.update_button_styles()
        self.post_message(self.Changed(self._configuration, self._session_name))
        logging.debug(
            f"Button {button_name} {'disabled' if self.check_button_state(button_name, self._button_list[button_name]) else 'enabled'}"
        )

    def _button_action(self, *args, **kwargs):
        raise NotImplementedError("Button action must be implemented")

    def generate_button_list(self):
        raise NotImplementedError("Generate button list must be implemented")

    class Changed(Message):
        """Custom message to notify when a button is pressed."""

        def __init__(self, configuration, session) -> None:
            super().__init__()
            self._configuration = configuration
            self._session = session

        @property
        def configuration(self):
            return self._configuration

        @property
        def session(self):
            return self._session

    def get_changed_states_as_str(self):
        output_str = ""

        for button, information in self._button_list.items():
            # Check if the button is disabled
            state = self.check_button_state(button, information)

            if state == self._default_states[button]:
                continue

            # Hacky but it means we can have readable buttons and textual can use them...
            button = button.replace(" ", "_")
            output_str += f"_{button}_{'on' if state else 'off'}"

        return output_str

    def get_current_states(self):
        # Return a dictionary of the current states for mapping purposes
        return {k: self.check_button_state(k, b) for k, b in self._button_list.items()}

    def get_full_state_info(self):
        # Full information is just the button list dict
        return self._button_list

    def update_button_styles(self):
        """Update the styles of the buttons based on their current state."""
        for button, information in self._button_list.items():
            button_id = button.replace(" ", "_") + "_button"
            try:
                button_widget = self.query_one(f"#{button_id}", Button)
            except Exception:
                return

            button_state = self.check_button_state(button, information)
            logging.info(f"Button {button} is {button_state}")

            button_widget.remove_class("detector_subsystem_button_enabled")
            button_widget.remove_class("detector_subsystem_button_partial")
            button_widget.remove_class("detector_subsystem_button_disabled")
            button_widget.disabled = False

            if button_state == SubsystemStatus.DISABLED:
                button_widget.add_class("detector_subsystem_button_disabled")
                button_widget.label = f"{button} (Disabled)"
            elif button_state == SubsystemStatus.ENABLED:
                button_widget.add_class("detector_subsystem_button_enabled")
                button_widget.label = f"{button} (Enabled)"

            elif button_state == SubsystemStatus.PARTIALLY_ENABLED:
                button_widget.add_class("detector_subsystem_button_partial")
                button_widget.label = f"{button} (Partially Enabled)"
            elif button_state == SubsystemStatus.TOP_LEVEL_DISABLED:
                button_widget.disabled = True
                button_widget.add_class("detector_subsystem_button_disabled")
                button_widget.label = f"{button} (Disabled)"

            else:
                raise ValueError(f"Unknown button state {button_state}")
