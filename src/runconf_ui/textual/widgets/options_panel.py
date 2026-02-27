from textual import on
from textual.widgets import Button
from textual.containers import ScrollableContainer

from ..messages import QuitMessage, SaveConfigMessage, ResetMessage, HelpMessage

class OptionsPanel(ScrollableContainer):
    '''
    Container for options (create, help, reset, quit)
    '''
    BUTTONS = [
        ("Create Run Configuration", "create_run_config", "primary"),
        ("Help", "help", "secondary"),
        ("Reset to Default", "reset", "warning"),
        ("Quit", "quit", "error"),
    ]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buttons = []
        self.generate_buttons()
        
    def generate_buttons(self):
        '''
        Generate buttons based on the predefined BUTTONS list
        '''
        for label, id_, cls in self.BUTTONS:
            button = Button(label=label, id=id_, classes=cls)
            self.buttons.append(button)
            self.mount(button)
    
    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed):
        '''
        Handle button press events and emit corresponding messages
        '''
        button_id = event.button.id
        if button_id == "quit":
            self.post_message(QuitMessage())
        elif button_id == "create_run_config":
            # For demonstration, we use a hardcoded config path.
            # In a real application, you would likely open a file dialog here.
            self.post_message(SaveConfigMessage())
        elif button_id == "help":
            # Handle help action (e.g., open a help dialog or webpage)
            self.post_message(HelpMessage())
        elif button_id == "reset":
            # Handle reset action (e.g., reset the configuration to default)
            self.post_message(ResetMessage())