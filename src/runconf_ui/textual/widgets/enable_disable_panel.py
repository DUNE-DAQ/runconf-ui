from textual import on
from textual.widgets import Button
from textual.containers import ScrollableContainer

from ..messages import NodeToggledMessage

class EnableDisablePanel(ScrollableContainer):
    '''
    Scrollable container that holds enable/disable buttons for DISABLE nodes.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buttons = []
        

    def generate_buttons(self, button_labels, button_ids, state, button_enabled):
        '''
        Generate buttons based on the provided labels, ids and classes
        '''
        for label, id_, cls, enabled in zip(button_labels, button_ids, state, button_enabled):
            class_="enable_disable_button " + cls
            
            button = Button(label=label, id=id_, classes=class_, disabled=not enabled)
            self.buttons.append(button)
            self.mount(button)
            
    def update_buttons(self, button_ids, state, button_enabled):
        '''
        Update the state and enabled status of existing buttons
        '''
        for id_, cls, enabled in zip(button_ids, state, button_enabled):
            button: Button = self.query_one(f"#{id_}", Button)
            button.set_class(False, cls, "enable_disable_button")
            button.disabled = not enabled
        
    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed):
        '''
        Handle button press events and emit a NodeToggledMessage with the button's id
        '''
        button_id = event.button.id
        self.post_message(NodeToggledMessage(widget_id=button_id))