'''
Builds and fills the main screen with buttons etc.
'''

from textual.widgets import Button, TabPane, TabbedContent
from runconf_ui.state_tree import Node
from runconf_ui.runconf_backend_wrapper.runconf_backend_wrapper import AddressBookEntry
from runconf_ui.system_configuration.config_reader import AssembledGroup, AssembledSystem
from runconf_ui.state_tree import labelled, Node, State, NodeStatus


def create_disable_button(syst: NodeStatus)->Button:
    '''
    Create a button for enable/disable
    '''
    return Button(
        label=syst.node.label,
        classes  = f"enable_disable_button f{str(syst.state).lower()}",
        disabled = syst.is_interactive,
        tooltip  = syst.node.label,
    )    

def build_disable_buttons(group: AssembledGroup)->list[Button]:
    '''
    This returns a list of buttons for a given AssembledGroup
    '''
    return [create_disable_button(s) for g in group.systems for s in labelled(g.root)]

