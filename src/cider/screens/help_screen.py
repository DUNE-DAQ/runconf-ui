from textual.widgets import Button, Label, TextArea, Static
from textual.containers import ScrollableContainer
from textual.screen import Screen

from textwrap import dedent

import cider.interfaces.actions.actions as ca
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper


class HelpScreen(Screen):
    """Help Screen pop up."""

    def compose(self):
        with ScrollableContainer(classes="pop_up scrollable_popup"):
            yield Static(
                self.message(),
                classes="help_message",
            )

        yield Button("Close", id="close_help_screen", classes="help_up_button")

    def message(self):
        return dedent(
            """\
            [bold]Hello and welcome to the DAQ Shifter interface!![/bold]

            To get started, please select a file from the dropdown menu and then select a session.  
            The configuration will be copied, and you can start enabling/disabling things in the detector.  

            Currently, 3 options are available:  
            - [bold]Detector Subsystem[/bold]
            - [bold]Dataflow Applications[/bold]
            - [bold]Triggers[/bold]

            You can enable/disable these options by clicking on the buttons.  
            When you're happy, you can save/copy + quit the configuration editor and run it through DRUNC.  

            In addition, you can reset all changes by pressing the reset button.  
        """
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_help_screen":
            self.app.pop_screen()
