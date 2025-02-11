import cider.interfaces.actions.actions as ca
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper

from cider.screens.quit_screen import QuitScreen
from cider.screens.help_screen import HelpScreen

from textual.containers import Vertical
from textual.visual import SupportsVisual
from textual.widgets import Button, Static
from pathlib import Path

class OptionPanel(Static):
    def __init__(
        self,
        configuration: ConfigurationWrapper | None,
        session: str | None,
        content: str | SupportsVisual = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            content,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

        self._configuration = configuration
        self._session_name = session

    def compose(self):
        
        disable_buttons = self._configuration is None or self._session_name is None
        
        
        yield Vertical(
            Button("[bold white]Help", id="help_button", classes="options_button"),
            Button(
                "[bold white]Save and Copy",
                id="save_and_copy_button",
                classes="options_button",
                disabled=disable_buttons
            ),
            # Button("[bold white]Save To Database", id="save_to_database_button", classes="options_button"),
            Button(
                "[bold white]Reset",
                id="undo_changes_button",
                classes="options_button",
                disabled=disable_buttons
            ),
            Button("[bold white]Quit", id="quit_button", classes="options_button"),
            id="option_panel",
            classes="options_panel"
        )

    def save_copy(self):
        ca.CopyFullConfigurationAction(self._configuration)(self.generate_output_name())        

    def generate_output_name(self):
        if self._configuration is None:
            return
        
        full_path = self.app.query_one("FileIOPanel").selected_config_name
        
        config_name = str(Path(full_path).stem)
        config_name = config_name.replace(".data", "")
        
        session = self.app.query_one("FileIOPanel").selected_session_name
        
        output_name = f"{config_name}_{session}"
        
        for a in self.app.query("EnableDisablePanel"):
            output_name+=f"{a.get_object_states()}"

        return f"{output_name}.data.xml"

    def open_new_session(self, configuration: ConfigurationWrapper | None, session_name: str | None):
        self._session_name = session_name
        self._configuration = configuration
        
        disable_buttons = self._configuration is None or self._session_name is None
        self.query_one("#save_and_copy_button").disabled = disable_buttons
        self.query_one("#undo_changes_button").disabled = disable_buttons

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "help_button":
            self.app.push_screen(HelpScreen(classes="pop_up_screen"))
        elif event.button.id == "save_and_copy_button":
            try:
                self.save_copy()
            except Exception as e:
                raise e
            
        elif event.button.id == "undo_changes_button":
            # Reset everything!
            try:
                self.app.get_screen("shifter_view_screen").open_new_file()
            except:
                pass

        elif event.button.id == "quit_button":
            
            if self._configuration is not None and self._session_name is not None:
                self.app.push_screen(
                    QuitScreen(
                        self._session_name,
                        self._configuration,
                        self.generate_output_name(),
                        classes="pop_up_screen",
                    )
                )
            else:
                self.app.exit("Exited without saving")
