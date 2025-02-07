import cider.interfaces.actions.actions as ca
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper

from textual.containers import Vertical
from textual.visual import SupportsVisual
from textual.widgets import Button, Static

class OptionPanel(Static):
    def __init__(self, configuration: ConfigurationWrapper, content: str | SupportsVisual = "", *, expand: bool = False, shrink: bool = False, markup: bool = True, name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False) -> None:
        super().__init__(content, expand=expand, shrink=shrink, markup=markup, name=name, id=id, classes=classes, disabled=disabled)

        self._configuration = configuration
    
    def compose(self):
        yield Vertical(
            Button("[bold white]Help", id="help_button", classes="options_button"),
            Button("[bold white]Save and Copy", id="save_and_copy_button", classes="options_button"),
            # Button("[bold white]Save To Database", id="save_to_database_button", classes="options_button"),
            Button("[bold white]Undo Changes", id="undo_changes_button", classes="options_button"),
            Button("[bold white]Quit", id="quit_button", classes="options_button"),
            
            id="option_panel"               
        )
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "help_button":
            pass
        elif event.button.id == "save_and_copy_button":
            pass
        elif event.button.id == "save_to_database_button":
            pass
        elif event.button.id == "undo_changes_button":
            pass
        elif event.button.id == "quit_button":
            pass
        else:
            pass
        
    
            
        