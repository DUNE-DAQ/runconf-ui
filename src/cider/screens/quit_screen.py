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

    def message(self, quit_without_saving: bool = False):
        if self._configuration is None:
            return "[bold red]Exited without saving."

        output = ""
        if quit_without_saving:
            output += "[bold red]WARNING!! Configuration was create using the create message so may not be up to date with all changes, be careful![/bold red]\n\n"

        output += f"[purple]To run[/purple] [bold blue]DRUNC[/bold blue] [purple]please copy/paste:[/purple]\n[bold green]drunc-unified-shell ssh-standalone {self._saved_configuration_name} {self._session_name}"
        return output

    def compose(self):
        button_disabled = self._configuration is None or self._session_name is None

        yield Grid(
            Label(f"[bold]Are you happy with the config?", id="quit_question"),
            # Button("Copy Command", variant="success", id="copy"),
            Button(
                "Quit and Create Config",
                variant="success",
                id="quit_screen_savequit_button",
                classes="pop_up_button quit_screen_button",
                disabled=button_disabled,
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
        main_screen = self.app.get_screen("shifter_view_screen")
        options = main_screen.query_one("OptionPanel")
        if event.button.id == "quit_screen_savequit_button":
            # HACK: This is a hack to save correctly
            options.save_copy()
            self._saved_configuration_name = options.saved_configuration

            self.app.exit(self.message())

        if event.button.id == "quit_screen_quit_button":

            # Check if we've saved something!
            if options.saved_configuration is None:
                self.app.exit("[bold red]Exited without saving.")
            else:
                self._saved_configuration_name = options.saved_configuration
                self.app.exit(self.message(True))
        else:
            self.app.pop_screen()
