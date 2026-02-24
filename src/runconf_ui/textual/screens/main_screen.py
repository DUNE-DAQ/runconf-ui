# runconf-ui
from ..widgets import generate_disable_buttons, ButtonWithNode
from runconf_ui.system_configuration.config_reader import AssembledGroup, AssembledSystem

# Textual imports
from textual.screen import ModalScreen
from textual.widgets import TabbedContent, TabPane, Button, Static
from textual.containers import ScrollableContainer
from textual import on

class ButtonPanel(Static):
    def compose(self, group: AssembledGroup):
        yield ScrollableContainer(*(b for b in generate_disable_buttons(group)))
    
    
    # @on(Button.Pressed)
    # def a
    
class OptionsPanel(ButtonPanel):
    ...
    
class DisablePanel(ButtonPanel):
    def compose(self, object_group: AssembledSystem):
        
    

class MainScreen(ModalScreen):
    ...