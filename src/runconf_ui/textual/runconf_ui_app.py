'''
Textual application for controlling runconf-shifter-ui
'''

from typing import ClassVar

from textual import on
from textual.app import App
from textual.widgets import Button

from runconf_ui.textual import messages as rc_msg
from runconf_ui.backend import (RunconfUI, RunconfContext)

class RunconfShifterUI(App):
    BINDINGS: ClassVar = [("ctrl+q", "quit", "Quit")]

    OPTIONS = ["QUIT", "REFRESH", "SAVE", "OPEN"]

    def __init__(
        self,
        context: RunconfContext,
        *args, **kwargs
    ):
        '''
        Main application, takes RunconfContext as an argument, initialises the application and takes context
        '''
        super().__init__(*args,**kwargs)
        self.backend = RunconfUI(context)
        
    @on(rc_msg.NodeToggledMessage)
    def handle_node_toggled(self, message: rc_msg.NodeToggledMessage):
        '''
        Handle NodeToggledMessage by calling the backend's toggle_node method with the widget_id from the message
        '''
        self.backend.toggle(message.widget_id)
        