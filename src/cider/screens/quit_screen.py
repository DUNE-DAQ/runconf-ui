from textual.widgets import Button, Label
from textual.containers import Grid
from textual.screen import Screen
import logging
import os
from pathlib import Path
import subprocess

from cider.interfaces.controller.config_wrapper import ConfigurationWrapper


class QuitScreen(Screen):
    """Screen with a dialog to quit."""

    def __init__(
        self,
        session: str = "",
        configuration: ConfigurationWrapper | None = None,
        render_no_create: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:

        super().__init__(name, id, classes)
        self._configuration = configuration
        self._session_name = session
        self._render_no_create = render_no_create

    def message(self, quit_without_saving: bool = False):
        """
        Message to display on quit
        """
        if self._configuration is None:
            return "[bold red]Exited without saving."

        # Set environment variables!
        run_mode = os.getenv('PROCESS_MANAGER_CONFIG')
        if run_mode is None:
            run_mode="ssh-standalone"
        else:
            run_mode = f"{run_mode}".strip(".json") 
        run_cmd = f"drunc-unified-shell {run_mode} {self._saved_configuration_name} {self._session_name}"

        # hacky
        buffer_id = os.environ.get("SESSION_NAME", os.getlogin())
        output_script = f"/tmp/shifter_configs-{buffer_id}/set_next_run.sh"

        with open(f"{output_script}", "w") as f:
            f.write(f"export EHN1_RUN_FILE={Path(self._saved_configuration_name).expanduser()}\n")
            f.write(f"export EHN1_RUN_CONFIG_ID={self._session_name}\n")
            f.write(f"export EHN1_RUN_COMMAND='{run_cmd}'\n")

        os.chmod(f"{output_script}", 0o755)

        run_alias = os.environ.get("EHN1_RC_LAUNCH", run_cmd)

        output = ""
        if quit_without_saving:
            output += "[bold red]WARNING!! Configuration was created earlier but you've quit without saving so this may not be up to date with all the changes you've made, be careful![/bold red]\n\n"

        output += f"[purple]To run[/purple] use [bold green]{run_alias}\n"
        # output += f"[purple]This will run:[/purple] [green]{run_cmd}"
        return output

    def compose(self):
        # We need to get the saved configuration name
        # TODO: Add a proper handler for this...
        main_screen = self.app.get_screen("shifter_view_screen")
        options = main_screen.query_one("OptionPanel")
        self._saved_configuration_name = options.saved_configuration

        # If the configuration is None, we can't save so let's not give the shifter the ability to do this
        button_disabled = self._configuration is None or self._session_name is None

        # This is a tad hacky but it means create+quit use the same screen
        if self._render_no_create:
            grid_classes = "pop_up quit_pop_up_grid quit_pop_up_grid_full"
            dialogue_class = "quit_question quit_question_full"
        else:
            grid_classes = "pop_up quit_pop_up_grid quit_pop_up_grid_small"
            dialogue_class = "quit_question quit_question_small"

        # Message to display on the popup
        if self._configuration is None:
            # If we've not loaded
            label = "No configuration loaded, quit?"
        else:
            # To make sure the shifter double checks
            label = f"Are you happy with the config stored in: {self._saved_configuration_name}"

        with Grid(id="quit_dialog", classes=grid_classes):

            # Button("Copy Command", variant="success", id="copy"),
            yield Label(f"[bold]{label}", id="quit_question", classes=dialogue_class)

            yield Button(
                "Create Config and Quit",
                variant="success",
                id="quit_screen_savequit_button",
                classes="pop_up_button quit_screen_button",
                disabled=button_disabled,
            )

            if self._render_no_create:
                yield Button(
                    "Quit Without Creating Config",
                    variant="warning",
                    id="quit_screen_quit_button",
                    classes="pop_up_button quit_screen_button",
                )

            yield Button(
                "Cancel and Continue Editing",
                variant="error",
                id="quit_screen_cancel_button",
                classes="pop_up_button quit_screen_button",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        main_screen = self.app.get_screen("shifter_view_screen")
        options = main_screen.query_one("OptionPanel")

        if event.button.id == "quit_screen_savequit_button":
            logging.info("Quitting and saved")

            # HACK: This is a hack to save correctly
            options.save_backup()
            options.save_main()

            self._saved_configuration_name = options.saved_configuration
            self.app.exit(self.message())

        if event.button.id == "quit_screen_quit_button":
            logging.info("Quitting without saving")
            # Check if we've saved something!
            if options.saved_configuration is None:
                self.app.exit("[bold red]Exited without saving.")

            else:
                options.save_backup()
                self._saved_configuration_name = options.saved_configuration
                # To be sure!
                self.app.exit(self.message(True))

        else:
            self.app.pop_screen()
