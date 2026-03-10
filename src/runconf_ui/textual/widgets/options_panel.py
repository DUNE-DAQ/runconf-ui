from textual import on
from textual.containers import ScrollableContainer
from textual.widgets import Button

from ..messages import (
    OpenCreateMenuMessage,
    OpenHelpMenuMessage,
    OpenQuitMenuMessage,
    ResetMessage,
)


class OptionsPanel(ScrollableContainer):
    '''
    Container for options (create, help, reset, quit)
    '''
    def __init__(self, *args, **kwargs):
        self.BUTTONS = [
            ("Create Run Configuration", "create_run_config", "success"),
            ("Help", "help", "primary"),
            ("Reset to Default", "reset", "warning"),
            ("Quit", "quit", "error"),
        ]

        super().__init__(*args, **kwargs)

    def compose(self):
        for label, button_id, style in self.BUTTONS:
            yield Button(label, id=button_id, variant=style, classes="options_button")

    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed):
        '''
        Handle button press events and emit corresponding messages
        '''
        button_id = event.button.id
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
            self.post_message(ResetMessage())