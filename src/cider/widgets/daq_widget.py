# Textual imports
from textual.widget import Widget
from textual.widgets import Static
from textual.message import Message
from textual import on

# CIDER imports
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.interfaces.actions.action_interfaces import ActionInterface
from cider.interfaces.actions.actions import GetAttributeAction

from typing import List, Callable


class DaqWidget(Widget):
    # Main reason for this is to give DAQ widgets access to the configuration
    # def __init__(self, configuration: ConfigurationWrapper, textual_widget: Widget,
    def __init__(
        self,
        configuration: ConfigurationWrapper,
        textual_widget: Widget | None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)

        self._widget = textual_widget
        self._configuration = configuration        
        self.get_attribute = GetAttributeAction(self._configuration)

        self._actions = {}

    def add_action_sequence(self, sequence_name: str, sequence: List[Callable]):
        """
        Adds a sequence of actions and dynamically registers an @on(sequence_name) handler.
        """
        self._actions[sequence_name] = sequence

    def compose(self):
        if self._widget is not None:
            yield self._widget

    def do_action_sequence(self, sequence_name: str, *args, **kwargs):
        """
        Executes a sequence of actions.
        """
        result = self._actions[sequence_name][0](*args, **kwargs)

        if len(self._actions[sequence_name]) == 1:
            return result

        for action in self._actions[sequence_name]:
            result = action(result)

    @property
    def widget(self):
        return self._widget