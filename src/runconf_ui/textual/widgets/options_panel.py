from textual import on
from textual.containers import ScrollableContainer
from textual.widgets import Button

from ..messages import (
    LoadConfigMessage,
    OpenCreateMenuMessage,
    OpenHelpMenuMessage,
    OpenQuitMenuMessage,
)
from runconf_ui.utils import get_logger


class OptionsPanel(ScrollableContainer):
    '''
    Container for options (create, help, reset, quit)
    '''
    def __init__(self, *args, **kwargs):
        self.BUTTONS = [
            ("Create Run Configuration", "create_run_config", "success", True),
            ("Help", "help", "primary", False),
            ("Reset to Default", "reset", "warning", True),
            ("Quit", "quit", "error", False),
        ]

        super().__init__(*args, **kwargs)
        get_logger().debug(f"Options panel initialised")

        self._config_loaded = False

    def compose(self):
        for label, button_id, style, disabled in self.BUTTONS:
            yield Button(label, id=button_id, variant=style, disabled=disabled, classes="options_button")
        get_logger().debug(f"Options panel composed")

    def enable_all(self):
        for button in self.query(Button):
            button.disabled=False
            
    def disable_selected(self):
        for _, id, _, init_state in self.BUTTONS:
            button = self.query_exactly_one(id)
            button.disabled = init_state

    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed):
        '''
        Handle button press events and emit corresponding messages
        '''
        button_id = event.button.id
        get_logger().debug(f"{button_id} pressed in options panel")

        if button_id == "quit":
            self.post_message(OpenQuitMenuMessage())
        elif button_id == "create_run_config":
            # For demonstration, we use a hardcoded config path.
            # In a real application, you would likely open a file dialog here.
            self.post_message(OpenCreateMenuMessage())
        elif button_id == "help":
            # Handle help action (e.g., open a help dialog or webpage)
            self.post_message(OpenHelpMenuMessage())
        elif button_id == "reset":
            # Handle reset action (e.g., reset the configuration to default)
            self.post_message(LoadConfigMessage())