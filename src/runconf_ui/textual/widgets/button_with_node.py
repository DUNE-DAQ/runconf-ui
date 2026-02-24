from typing import Iterable
from typing_extensions import Self

from textual import on
from textual.widgets import Button
from runconf_ui.state_tree import NodeStatus

class ButtonWithNode(Button):
    '''
    Button containing a node for ease of communicating
    '''
    def __init__(self, node_status: NodeStatus):
        self.node_status = node_status
        

        super().__init__(label   = node_status.node.label,
                        classes  = self.node_class_str,
                        disabled = node_status.is_interactive,
                        tooltip  = node_status.node.label)

    @property
    def node_class_str(self):
        '''Quickly change colour by changing the classes in the widget'''
        return f"enable_disable_button f{str(self.node_status.state).lower()}"

    def refresh_status(self):
        '''Refresh the widget status'''
        self.disabled = self.node_status.is_interactive
        self.set_classes(self.node_class_str)
        
    @on(Button.Pressed)
    def 