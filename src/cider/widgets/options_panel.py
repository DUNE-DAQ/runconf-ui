import cider.interfaces.actions.actions as ca
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.screens.quit_screen import QuitScreen
from cider.screens.help_screen import HelpScreen
from cider.widgets.popup_message import PopupMessage

from textual.reactive import reactive

from textual.css.query import NoMatches
from textual.containers import ScrollableContainer
from textual.visual import SupportsVisual
from textual.widgets import Button, Static
from pathlib import Path
from datetime import datetime
import shutil
import logging

class OptionPanel(Static):
    show_popup = reactive(False)

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

    def get_config_session(self):
        return self._configuration, self._session_name

    def show_popup(self, message: str):
        """
        Display a pop-up message on the screen.
        """
        # Remove any existing pop-up to avoid duplicates
        self.remove_popup()

        # Create and mount the pop-up
        popup = PopupMessage(message, classes="popup popup_success")
        
        main_screen = self.app.get_screen("shifter_view_screen")
        main_screen.query_one("#main_container").mount(popup)

    def remove_popup(self):
        """
        Remove any existing pop-up from the screen.
        """
        try:
            # Find and remove any existing pop-up
            existing_popup = self.query_one(".popup", expect_type=PopupMessage)
            existing_popup.remove()
        except NoMatches:
            # No pop-up to remove
            pass

    def compose(self):
        logging.debug("OptionPanel compose")
        disable_buttons = self._configuration is None or self._session_name is None

        yield ScrollableContainer(
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


    def save_to_path(self, dir_path, name):
        logging.info(f"Saving configuration to {dir_path}/{name}")
        
        dir_path = Path(dir_path)
        
        # Clear it
        if dir_path.is_dir():
            shutil.rmtree(dir_path)
        
        dir_path.mkdir(parents=True, exist_ok=True)
        
        output_file_path = f"{dir_path}/{name}"
        
        logging.debug(f"Copying configuration to {output_file_path}")
        ca.CopyFullConfigurationAction(self._configuration)(output_file_path)
        self.generate_change_log(output_file_path)

        logging.info(f"Configuration saved to {output_file_path}")
        return output_file_path

    # Wrappers
    def save_main(self):        
        self._saved_configuration = self.save_to_path(f"{self._output_directory}/current_config", self.generate_output_name())
        self.show_popup(
            f"[white]Configuration saved to [bold grey3]{self._saved_configuration}[/bold grey3]"
        )



    def save_backup(self):
        self.save_to_path(f"{self._output_directory}/old_configs/run_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}", self.generate_output_name())

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
                self.save_main()
                self.save_backup()
                self.app.push_screen(
                    QuitScreen(
                        self._session_name,
                        self._configuration,
                        render_no_create=False,
                        classes="pop_up_screen",
                    )
                )

            except Exception as e:
                logging.error(f"Error saving configuration: {e}")
                self.show_popup(
                    f"[white]Invalid configuration[/white] [bold grey3]{self.query_one(FileIOPanel).selected_config_name}:{self.query_one(FileIOPanel).selected_session_name}[/bold grey3] [white]passed, please check with the experts!\n\
                    Log saved to[/white] [bold grey3]{logging.getLogger().handlers[0].baseFilename}[/bold grey3]"
                )
        elif event.button.id == "undo_changes_button":
            # Reset everything!
            logging.debug("Reset button pressed")
            self.app.get_screen("shifter_view_screen").open_new_file()

        elif event.button.id == "quit_button":
            logging.debug("Quit button pressed")
            self.app.push_screen(
                QuitScreen(
                    self._session_name,
                    self._configuration,
                    classes="pop_up_screen",
                )
            )
