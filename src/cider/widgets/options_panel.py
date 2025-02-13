import cider.interfaces.actions.actions as ca
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper

from cider.screens.quit_screen import QuitScreen
from cider.screens.help_screen import HelpScreen

from textual.containers import Vertical
from textual.visual import SupportsVisual
from textual.widgets import Button, Static
from pathlib import Path
from datetime import datetime
import shutil


class OptionPanel(Static):
    def __init__(
        self,
        configuration: ConfigurationWrapper | None,
        session: str | None,
        output_directory: str,
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
        self._output_directory = output_directory
        self._saved_configuration = None

    @property
    def saved_configuration(self):
        return self._saved_configuration

    def compose(self):

        disable_buttons = self._configuration is None or self._session_name is None

        yield Vertical(
            Button("[bold white]Help", id="help_button", classes="options_button"),
            Button(
                "[bold white]Create",
                id="create_button",
                classes="options_button",
                disabled=disable_buttons,
            ),
            # Button("[bold white]Save To Database", id="save_to_database_button", classes="options_button"),
            Button(
                "[bold white]Reset",
                id="undo_changes_button",
                classes="options_button",
                disabled=disable_buttons,
            ),
            Button("[bold white]Quit", id="quit_button", classes="options_button"),
            id="option_panel",
            classes="options_panel",
        )

    def save_copy(self):
        # Check output directory
        main_output_path = Path(f"{self._output_directory}/current_config")
        backup_output_path = Path(
            f"{self._output_directory}/old_configs/run_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        )

        if main_output_path.is_dir():
            shutil.rmtree(main_output_path)

        main_output_path.mkdir(parents=True, exist_ok=True)
        backup_output_path.mkdir(parents=True, exist_ok=True)

        main_copy = f"{main_output_path}/{self.generate_output_name()}"
        backup_copy = f"{backup_output_path}/{self.generate_output_name()}"

        # Make current copy
        ca.CopyFullConfigurationAction(self._configuration)(main_copy)
        self.generate_change_log(main_copy)
        # Make backup copy
        ca.CopyFullConfigurationAction(self._configuration)(backup_copy)
        self.generate_change_log(backup_copy)

        self._saved_configuration = main_copy

    def generate_output_name(self):
        if self._configuration is None:
            return

        main_screen = self.app.get_screen("shifter_view_screen")

        full_path = main_screen.query_one("FileIOPanel").selected_config_name

        config_name = str(Path(full_path).stem)
        config_name = config_name.replace(".data", "")

        session = main_screen.query_one("FileIOPanel").selected_session_name

        output_name = f"{config_name}_{session}"

        return f"{output_name}.data.xml"

    def generate_change_log(self, config_path):
        log_name = config_path.replace(".data.xml", "_changes.txt")

        main_screen = self.app.get_screen("shifter_view_screen")

        with open(f"{log_name}", "w") as file:

            for a in main_screen.query("EnableDisablePanel"):
                current_states = a.get_current_states()
                file.write(f"\n{a.id}\n")
                file.write(f"{'-' * len(a.id)}\n")
                for key, value in current_states.items():
                    file.write(f"{key} : {'disabled' if value else 'enabled'}\n")

    def open_new_session(
        self, configuration: ConfigurationWrapper | None, session_name: str | None
    ):
        self._session_name = session_name
        self._configuration = configuration

        disable_buttons = self._configuration is None or self._session_name is None
        self.query_one("#create_button").disabled = disable_buttons
        self.query_one("#undo_changes_button").disabled = disable_buttons

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "help_button":
            self.app.push_screen(HelpScreen(classes="pop_up_screen"))
        elif event.button.id == "create_button":
            try:
                self.save_copy()
            except Exception as e:
                raise e

        elif event.button.id == "undo_changes_button":
            # Reset everything!
            try:
                self.app.get_screen("shifter_view_screen").open_new_file()
            except Exception as e:
                pass

        elif event.button.id == "quit_button":

            self.app.push_screen(
                QuitScreen(
                    self._session_name,
                    self._configuration,
                    classes="pop_up_screen",
                )
            )
