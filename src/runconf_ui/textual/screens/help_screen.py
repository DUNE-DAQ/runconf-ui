from textwrap import dedent
from typing import ClassVar

from textual.containers import ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class HelpScreen(ModalScreen):
    BINDINGS: ClassVar[list] = [("escape", "app.pop_screen", "Close")]

    def __init__(self):
        super().__init__(classes="pop_up_screen")

    def compose(self):
        with Vertical(classes="pop_up help_popup_container"):
            with ScrollableContainer(classes="help_scroll"):
                yield Static(self.message(), classes="help_message")
            yield Button(
                "Close (Esc)", id="close_help_screen", classes="help_up_button"
            )

    def message(self):
        """Generate the help message text.

        :returns: Formatted help text with Rich markup
        :rtype: str
        """
        return dedent("""\
            [bold]Hello and welcome to Runconf-shifter UI!![/bold]
            To get started, please select the following from dropdown menus:
                1. The DAQ version you would like to use 
                2  Once this is selected, select the session you would like to access
                3. Press Open
            
            This will spawn 2 panels
            1. The Enable/Disable Panel (left)
            2. The map/adjustable attribute panel (right)

            [bold]Enable Disable Panel[/bold]
            These tabs contain everything in the detector that can be toggled on/off. 
            To toggle an object on/off press the button. If a parent of the object
            is switched off, the buttton will not be pressable.
    
            To see these relationships you can use the map panels.
            
            [bold]Map Panels[/bold]
            The panels on the right contain 3 elements. We will first look at
            the "System Maps" and "Configuration" views. 
            
            Configuration is an overview of a large subset of objects within the
            detector. It gives you a global view of what's currently enable/disabled
            
            The System Maps give you maps of elements in the Enable/Disable Panel. 
            This can tell you exactly what the panels are turning on and off.
            
            [bold]Adjustable Attributes[/bold]
            Finally, we can look at the adjustable attributes. Adjustable attributes
            are things we want to set the value of before the run, for example,
            trigger rates.
            
            [bold]Creating a Configuration[/bold]
            Once you're done modifying the configuration, simply press "create".
            This will generate a configuration file and your terminal
            will tell you how to use this with DRUNC.

        """)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press events to close the help screen.

        :param event: The Button.Pressed event
        """

        if event.button.id == "close_help_screen":
            self.app.pop_screen()
