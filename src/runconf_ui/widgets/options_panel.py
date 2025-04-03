import runconf_ui.interfaces.actions.actions as ca
from runconf_ui.interfaces.controller.config_wrapper import ConfigurationWrapper
from runconf_ui.screens.quit_screen import QuitScreen
from runconf_ui.screens.help_screen import HelpScreen
from runconf_ui.widgets.popup_message import PopupMessage
from runconf_ui.utils.file_cleaner import clean_old_files
from runconf_ui.widgets.file_select_panel import FilePanelWidget

from textual.css.query import NoMatches
from textual.containers import ScrollableContainer
from textual.visual import SupportsVisual
from textual.widgets import Button, Static
from pathlib import Path
from datetime import datetime
import shutil
import logging
from runconf_ui.interfaces.controller.application_controller import ShifterInterfaceState


class OptionPanel(Static):
    def __init__(
        self,
        application_controller: ShifterInterfaceState,
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

        self._application_controller = application_controller

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
        disable_buttons = self._application_controller.session_name is None

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

        # Clear itz
        if dir_path.is_dir():
            shutil.rmtree(dir_path)

        dir_path.mkdir(parents=True, exist_ok=True)

        output_file_path = f"{dir_path}/{name}"

        logging.debug(f"Copying configuration to {output_file_path}")
        ca.CopyFullConfigurationAction(
            self._application_controller.dummy_oks_configuration
        )(output_file_path)
        self.generate_change_log(output_file_path)

        logging.info(f"Configuration saved to {output_file_path}")
        return output_file_path

    # Wrappers
    def save_main(self):
        self._application_controller.saved_configuration = self.save_to_path(
            f"{self._application_controller.interface_config.output_directory}/current_config",
            self.generate_output_name(),
        )
        self.show_popup(
            f"[white]Configuration saved to [bold grey3]{self._application_controller.saved_configuration}[/bold grey3]"
        )

    def save_backup(self):
        self.save_to_path(
            f"{self._application_controller.interface_config.output_directory}/old_configs/run_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}",
            self.generate_output_name(),
        )
        clean_old_files(
            Path(
                f"{self._application_controller.interface_config.output_directory}/old_configs"
            ),
            extension=".data.xml",
            n_files=5,
            include_folders=True,
            folder_prefix="run_",
        )

    def generate_output_name(self):
        # Hacky method to talk to the main screen
        full_path = self._application_controller.oks_configuration

        config_name = str(Path(full_path).name)
        config_name = config_name.replace(".data.xml", "")
        session = self._application_controller.session_name

        output_name = f"{config_name}_{session}"

        return f"{output_name}.data.xml"

    def generate_change_log(self, config_path):
        """
        Makes a log containing a summary of what was changed in the configuration
        """
        log_name = config_path.replace(".data.xml", "_changes.txt")

        main_screen = self.app.get_screen("shifter_view_screen")

        with open(f"{log_name}", "w") as file:

            for a in main_screen.query("EnableDisablePanel"):
                current_states = a.get_current_states()
                file.write(f"\n{a.id}\n")
                file.write(f"{'-' * len(a.id)}\n")
                for key, value in current_states.items():
                    file.write(f"{key} : {value.name}\n")

    def open_new_session(
        self,
    ):
        disable_buttons = self._application_controller.session_name is None
        self.query_one("#create_button").disabled = disable_buttons
        self.query_one("#undo_changes_button").disabled = disable_buttons

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "help_button":
            self.app.push_screen(HelpScreen(classes="pop_up_screen"))
        elif event.button.id == "create_button":
            # Try to create a new config
            try:
                self.save_main()
                self.save_backup()
                self.app.push_screen(
                    QuitScreen(
                        application_controller=self._application_controller,
                        render_no_create=False,
                        classes="pop_up_screen",
                    )
                )

            # Make sure what we do is valid
            except Exception as e:
                main_screen = self.app.get_screen("shifter_view_screen")

                logging.error(f"Error saving configuration: {e}")
                self.show_popup(
                    f"[white]Invalid configuration[/white] [bold grey3]{self._application_controller.oks_configuration}:{self._application_controller.session_name}[/bold grey3] [white]passed, please check with the experts!"
                )

        # Resets to base config provided
        elif event.button.id == "undo_changes_button":
            # Reset everything!
            logging.debug("Reset button pressed")
            self.app.get_screen("shifter_view_screen").open_new_file()

        # Quit
        elif event.button.id == "quit_button":
            logging.debug("Quit button pressed")
            return self.app.action_quit()
