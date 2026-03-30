from textual import on
from textual.containers import ScrollableContainer
from textual.widgets import Button

from runconf_ui.utils import get_logger

from ..messages import (
    LoadConfigMessage,
    OpenCreateMenuMessage,
    OpenHelpMenuMessage,
    OpenQuitMenuMessage,
)


class OptionsPanel(ScrollableContainer):
    """Container widget displaying control buttons for application options.

    Provides buttons for create, help, reset, and quit operations. Manages
    button enabled/disabled state based on whether a configuration is loaded.
    """

    def __init__(self, *args, **kwargs):
        """Initialize OptionsPanel with button definitions.

        :param args: Variable positional arguments passed to parent ScrollableContainer
        :param kwargs: Variable keyword arguments passed to parent ScrollableContainer
        """
        self.BUTTONS = [
            ("Create Run Configuration", "create_run_config", "success", True),
            ("Help", "help", "primary", False),
            ("Reset to Default", "reset", "warning", True),
            ("Quit", "quit", "error", False),
        ]

        super().__init__(*args, **kwargs)
        get_logger().debug("Options panel initialised")

        self._config_loaded = False

    def compose(self):
        """Compose all option buttons.

        :returns: A generator yielding Button widgets
        """
        for label, button_id, style, disabled in self.BUTTONS:
            yield Button(
                label,
                id=button_id,
                variant=style,
                disabled=disabled,
                classes="options_button",
            )
        get_logger().debug("Options panel composed")

    def enable_all(self):
        """Enable all option buttons for interaction."""
        for button in self.query(Button):
            button.disabled = False

    def disable_selected(self):
        """Disable buttons to their initial configured disabled states."""
        for _, id, _, init_state in self.BUTTONS:
            button = self.query_exactly_one(id)
            button.disabled = init_state

    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed):
        """Handle button press events and emit corresponding application messages.

        Routes button presses to emit the appropriate message:
        - quit: OpenQuitMenuMessage
        - create_run_config: OpenCreateMenuMessage
        - help: OpenHelpMenuMessage
        - reset: LoadConfigMessage

        :param event: The Button.Pressed event
        """
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
            self.post_message(LoadConfigMessage())
