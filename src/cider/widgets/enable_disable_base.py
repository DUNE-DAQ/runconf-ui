from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
import cider.interfaces.actions.actions as ca
from cider.utils.daq_conf_tree import DaqConfTree

from textual.geometry import Region
from textual.visual import SupportsVisual
from textual.widgets import Static, Placeholder, Button
from textual.containers import Grid, ScrollableContainer
from textual.message import Message
from typing import List


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

        self._default_states = {
            k: self.check_is_disabled(k, b) for k, b in self._button_list.items()
        }

        self.post_message(self.Changed(self._configuration, self._session_name))

    def check_is_disabled(self, button: str, information: str | List[str]) -> bool:
        return True

    def compose(self):
        with ScrollableContainer(id="buttons_panel"):
            for button, information in self._button_list.items():

                if self.check_is_disabled(button, information):
                    name_str = f"{button} (Disabled)"
                    classes = (
                        "detector_subsystem_button detector_subsystem_button_disabled"
                    )

                else:
                    name_str = f"{button} (Enabled)"
                    classes = (
                        "detector_subsystem_button detector_subsystem_button_enabled"
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
        self.post_message(self.Changed(self._configuration, self._session_name))

    def _button_action(self, objs_affected, button_name):
        pass

    def generate_button_list(self):
        return {}

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
            state = self.check_is_disabled(button, information)

            if state == self._default_states[button]:
                continue

            button = button.replace(" ", "_")
            output_str += f"_{button}_{'on' if state else 'off'}"

        return output_str

    def get_current_states(self):
        return {k: self.check_is_disabled(k, b) for k, b in self._button_list.items()}

    def get_full_state_info(self):
        return self._button_list
