# APPLE: Accessible Platform for Plain and Lightweight Editing

from cider.screens.shifter_view_screen import ShifterViewScreen
from cider.screens.quit_screen import QuitScreen

from textual.logging import TextualHandler
from textual.app import App
from textual.driver import Driver
import click
from rich import print

import os
from pathlib import Path
import logging
from datetime import datetime


class ShifterView(App):
    """
    Main app for the shifter view interface.
    """

    CSS_PATH = "shifter_view.tcss"
    BINDINGS = [("ctrl+q", "quit", "Quit")]

    def __init__(
        self,
        configuration_folder: str,
        output_directory: str,
        interface_config: str = "",
        log_level: str="INFO",

        driver_class: type[Driver] | None = None,
        css_path: str | None = None,
        watch_css: bool = False,
        ansi_color: bool = False,
    ):
        """Constructor for the ShifterView class."""
        super().__init__(driver_class, css_path, watch_css, ansi_color)

        # Make the logging directory if it doesn't exist
        logging_path = Path(f"{output_directory}/logs")
        logging_path.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            filename=f"{logging_path}/shifter_view_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log",
            format='%(asctime)s %(message)s',
            level=log_level,
        )


        self._configuration_folder = configuration_folder
        self._interface_config = interface_config
        self._output_directory = output_directory
        self._exit_message = ""
        
        
        
    def on_mount(self):
        """
        Mount App
        """
        self.theme = "catppuccin-latte"

        self.install_screen(
            ShifterViewScreen(
                self._configuration_folder,
                interface_config=self._interface_config,
                output_directory=self._output_directory,
            ),
            name="shifter_view_screen",
        )
        # Start with the SelectFileSessionScreen
        self.push_screen("shifter_view_screen")

    def action_quit(self):
        """Quit the application."""
        shifter_view = self.get_screen("shifter_view_screen")
        config, session = shifter_view.query_one("#option_panel_main").get_config_session()
    
        self.push_screen(QuitScreen(
            session,
            config,
            classes="pop_up_screen",
        ))

    def exit(self, message: str | None = None) -> None:
        """Override the exit method to store the exit message."""
        
        if message is not None:
            self._exit_message = message
        else:
            self._exit_message = "[bold red]Force exiting the application!!!"
        super().exit()  # Call the original exit method

    def exit_message(self) -> str:
        """Return the exit message."""
        return self._exit_message


@click.command()
@click.option(
    "-d",
    "--input-directory",
    "input_directory",
    default=os.getenv("DUNEDAQ_DB_PATH", ""),
    required=False,
)
@click.option(
    "-o", "--output-directory", "output_directory", default=".", required=False
)
@click.option(
    "-c",
    "--interface_config",
    "interface_config",
    default=f"{Path(__file__).parent.absolute()}/../configuration/np02_configuration.yml",
    required=False,
)
@click.option(
    "-l", "--log-level", "log_level", default="INFO", required=False
)


def main(input_directory, output_directory, interface_config, log_level):
    app = ShifterView(input_directory, output_directory, interface_config, log_level)
    app.run()
    print(app.exit_message())


if __name__ == "__main__":
    main()
 