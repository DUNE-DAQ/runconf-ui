'''
Textual application for controlling runconf-shifter-ui
'''

from textual.app import App
from typing import ClassVar

from runconf_ui.interface_layer import (RunconfUI,
                                                RunconfContext)

    

class RunconfShifterUI(App):
    BINDINGS: ClassVar = [("ctrl+q", "quit", "Quit")]

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
