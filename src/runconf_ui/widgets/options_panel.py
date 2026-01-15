import logging

from textual.containers import ScrollableContainer
from textual.message import Message
from textual.visual import SupportsVisual
from textual.widgets import Button, Static

from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)
from runconf_ui.screens.help_screen import HelpScreen
from runconf_ui.screens.popup_manager import PopupManager
from runconf_ui.screens.quit_screen import QuitScreen


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
                self.app.push_screen(
                    QuitScreen(
                        application_controller=self._application_controller,
                        render_no_create=False,
                        classes="pop_up_screen",
                    )
                )

            # Make sure what we do is valid
            except Exception as e:
                logging.error(f"Error saving configuration: {e}")
                popup = PopupManager(self.app.get_screen("shifter_view_screen"))

                popup.show(
                    f"[white]Invalid configuration[/white] [bold grey3]{self._application_controller.current_daq_config}:{self._application_controller.session_name}[/bold grey3] [white]passed, please check with the experts!",
                    timer=4.0,
                    success=False,
                )

        # Resets to base config provided
        elif event.button.id == "undo_changes_button":
            # Reset everything!
            logging.info("Reset button pressed")
            self.post_message(self.ResetPressed())
            # self.app.get_screen("shifter_view_screen").select_new_file()

        # Quit
        elif event.button.id == "quit_button":
            logging.debug("Quit button pressed")
            return self.app.action_quit()

    class ResetPressed(Message): ...
