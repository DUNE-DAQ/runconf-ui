'''
Builds and fills the main screen with buttons etc.
'''

from runconf_ui.state_tree import Node
from runconf_ui.interface_layer.runconf_ui import AddressBookEntry
from runconf_ui.system_configuration.config_reader import AssembledGroup, AssembledSystem
from runconf_ui.state_tree import labelled, Node, State, NodeStatus

from typing import Generator

from textual.widgets import Button, TabPane, TabbedContent
from .button_with_node import ButtonWithNode


def generate_disable_buttons(group: AssembledGroup)->Generator[ButtonWithNode]:
    '''
    This returns a list of buttons for a given AssembledGroup
    '''
    for g in group.systems:
        for s in labelled(g.root):
            yield ButtonWithNode(node_status = s)