# Textual imports
from textual.widget import Widget
from textual.widgets import Static
from textual.message import Message
from textual import on

# CIDER imports
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.interfaces.actions.action_interfaces import ActionInterface

from typing import List

class DaqWidget(Static):
    # Main reason for this is to give DAQ widgets access to the configuration
    # def __init__(self, configuration: ConfigurationWrapper, textual_widget: Widget,
    def __init__(self, configuration: ConfigurationWrapper, textual_widget: Widget, renderable= "", *, expand: bool = False, shrink: bool = False, markup: bool = True, name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False) -> None:
        super().__init__(renderable, expand=expand, shrink=shrink, markup=markup, name=name, id=id, classes=classes, disabled=disabled)             
    
        self._widget = textual_widget
        self._configuration = configuration
        self._actions = {}

    def add_action_sequence(self, sequence_name: str, sequence: List[ActionInterface]):
        """
        Adds a sequence of actions and dynamically registers an @on(sequence_name) handler.
        """
        self._actions[sequence_name] = sequence

    def compose(self):
        yield self._widget


    def do_action_sequence(self, sequence_name: str, *args, **kwargs):
        """
        Executes a sequence of actions.
        """
        result = self._actions[sequence_name][0](*args, **kwargs)

        if len(self._actions[sequence_name])==1:
            return result


        for action in self._actions[sequence_name]:
            result = action(result)