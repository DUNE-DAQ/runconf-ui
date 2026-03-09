from textual import on
from textual.containers import ScrollableContainer
from textual.widgets import Button, TabbedContent, TabPane
from textual.css.query import NoMatches

from runconf_ui.state_tree import NodeStatus

from ..messages import NodeToggledMessage

class EnableDisablePanel(ScrollableContainer):
    '''
    Scrollable container that holds enable/disable buttons for DISABLE nodes.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buttons = []
        

    def add_buttons(self, nodes: dict[str, NodeStatus]):
        '''
        Add buttons based on the provided labels, ids and classes
        '''
        for node_id, node in nodes.items():
            label  = node.node.label
            id_    = node_id
            cls    = "node_enabled" if node.is_enabled else "node_disabled"
            class_ = "enable_disable_button " + cls
            # Here 
            enabled = node.is_interactive
            

            button = Button(label=label, id=id_, classes=class_, disabled=not enabled)
            self.buttons.append(button)
            self.mount(button)
            
    def update_buttons(self, nodes: dict[str, NodeStatus]):
        '''
        Update the state and enabled status of existing buttons
        '''
        for node_id, node in nodes.items():
            cls = "node_enabled" if node.is_enabled else "node_disabled"
            enabled = node.is_interactive
            button: Button = self.query_one(f"#{node_id}", Button)
            button.set_class(False, cls, "enable_disable_button")
            button.disabled = not enabled
        
    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed):
        '''
        Handle button press events and emit a NodeToggledMessage with the button's id
        '''
        button_id = event.button.id
        group_id = self.id
        self.post_message(NodeToggledMessage(group_id=group_id, widget_id=button_id))
        
class EnableDisableTabs(TabbedContent):
    '''
    TabbedContent container that holds EnableDisablePanel instances for each group.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panels = {}
        
    def generate_panels(self, group_nodes: dict[str, dict[str, NodeStatus]]):
        '''
        Generate EnableDisablePanel instances for each group based on the provided dictionary of nodes.
        '''
        panels = []
        for group_name, node_info in group_nodes:
            panel = EnableDisablePanel(id=f"enable_disable_panel_{group_name}")
            panel.add_buttons(node_info)
            panels.append(panel)
            
        self.mount(TabPane(title="enable_disable_tabs", *panels))
            
    def update_panels(self, group_nodes: dict[str, dict[str, NodeStatus]]):
        '''
        Update the buttons in existing panels based on the provided dictionary of nodes.
        '''
        for group_id, nodes in group_nodes.items():
            try:
                panel = self.query_one(f"#enable_disable_panel_{group_id}", EnableDisablePanel)
            # Handle quietly for NoMatches
            except NoMatches:
                continue
            except Exception as e:
                raise e
    
            panel.update_buttons(nodes)