# APPLE: Accessible Platform for Plain and Lightweight Editing

from cider.screens.shifter_view_screen import ShifterViewScreen

from textual.app import App
from textual.driver import Driver
from textual.binding import Binding
import click

import os

class ShifterView(App):
    CSS_PATH="shifter_view.tcss"
    
    def __init__(
        self,
        configuration_folder: str,
        driver_class: type[Driver] | None = None,
        css_path: str | None = None,
        watch_css: bool = False,
        ansi_color: bool = False,
    ):
        super().__init__(driver_class, css_path, watch_css, ansi_color)

        self._configuration_folder = configuration_folder
        self._exit_message = ""

    def exit_message(self):
        return self._exit_message

    def on_mount(self):
        self.theme = "catppuccin-latte"

        self.install_screen(
            ShifterViewScreen(self._configuration_folder),
            name="main",
        )

        # Start with the SelectFileSessionScreen
        self.push_screen("main")

    def exit(self, message: str | None = None) -> None:
        """Override the exit method to store the exit message."""
        self._exit_message = message
        super().exit()  # Call the original exit method


@click.command()
@click.option("-d", "--input-directory", "input_directory", default="", required=True)
def main(input_directory):
    # CONFIGURATION_PATH = "/home/hwallace/scratch/dune_software/daq/daq_work_areas/NFD_DEV_241218_A9/nd_generated_file/"

    app = ShifterView(input_directory)
    app.run()
    print("To run DRUNC please copy/paste: ")
    print(app.exit_message())
