from textual.widgets import Button, Label
from textual.containers import Grid
from textual.screen import Screen

import cider.interfaces.actions.actions as ca
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper


class QuitScreen(Screen):
    """Screen with a dialog to quit."""

    def __init__(
        self,
        session: str = "",
        configuration: ConfigurationWrapper | None = None,
        new_configuration_name: str = "",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:

        super().__init__(name, id, classes)
        self._configuration = configuration
        self._session_name = session
        self._new_configuration_name = new_configuration_name

    def message(self):
        if self._configuration is None:
            return "[bold red]Exited without saving."

        return f"[purple]To run[/purple] [bold blue]DRUNC[/bold blue] [purple]please copy/paste:[/purple]\n[bold green]drunc-unified-shell ssh-standalone {self._configuration.file_name} {self._session_name}"

    def compose(self):
        yield Grid(
            Label(f"[bold]Are you happy with the config?", id="quit_question"),
            # Button("Copy Command", variant="success", id="copy"),
            Button(
                "Quit and Save",
                variant="success",
                id="quit_screen_savequit_button",
                classes="pop_up_button quit_screen_button",
            ),
            Button(
                "Quit Without Saving",
                variant="warning",
                id="quit_screen_quit_button",
                classes="pop_up_button quit_screen_button",
            ),
            Button(
                "Cancel",
                variant="error",
                id="quit_screen_cancel_button",
            classes="pop_up_button quit_screen_button",
            ),
            id="quit_dialog",
            classes="pop_up quit_pop_up",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit_screen_savequit_button":
            try:
                ca.CopyFullConfigurationAction(self._configuration)(self._new_configuration_name)
            except:
                pass

            self.app.exit(self.message())

        if event.button.id == "quit_screen_quit_button":
            self.app.exit(self.message())
        else:
            self.app.pop_screen()
