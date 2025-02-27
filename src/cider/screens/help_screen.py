from textual.widgets import Button, Static
from textual.containers import ScrollableContainer
from textual.screen import Screen

from textwrap import dedent


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

            To get started, please select the following from dropdown menus:
                1. The DAQ version you would like to use 
                2 Once this is selected, select the branch you would like to access

            the system will now quickly pause and open the correct configuration file. Finally:
            
                3. Select the session and press "open"
                
            Once this has been opened properly you will be greeted with the main interface.
            
            Currently there are 3 categories of objects that can be enabled or disabled:
            - [bold]Detector subsystems[/bold]: For example the APAs, PDS, etc.
            - [bold]The Trigger System[/bold]: Triggers to enable/disable including trigger primitive generation
            - [bold]Dataflow applications[/bold]: Objects that control dataflow
            
            To disable/enable items simply press the buttons on the left side of the screen. Each set of objects is given its own tab.
            In addition, we provide 3 views of the detector configuration, although this is mostly intended for expert use.
            - [bold]Configuration view[/bold]: View a tree describing detector configuration
            - [bold]Detector system view[/bold]: Summary of detector subsystems which are enabled/disabled
            - [bold]Trigger View[/bold]: A summary of triggers/trigger objects which are enabled/disabled 
            
            Once you have made the desired changes, press the "Create" button to save the configuration. By default the current configuration is saved in the <RUN FOLDER>/current_config directory.
            Older configurations are automatically moved to <RUN FOLDER>/old_configs/run_<DATE> when a new configuration is saved. 
            
            If you are unhappy with changes + want to revert to the original configuration, press the "Reset" button.
            
            Finally to quit the interface, press the "Quit" button. The configuration can be run in drunc using the command provided after quitting.
            
            If you have any questions, please contact the DAQ shifter on duty. Enjoy your shift!!
        """
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_help_screen":
            self.app.pop_screen()
