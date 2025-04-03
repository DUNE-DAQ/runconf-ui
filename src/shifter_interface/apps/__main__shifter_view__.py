"""
Main application for the shifter view interface.
"""

from runconf_ui.screens.shifter_view_screen import ShifterViewScreen
from runconf_ui.screens.quit_screen import QuitScreen
from runconf_ui.utils.file_cleaner import clean_old_files
from runconf_ui.utils.shifter_config_reader import ShifterConfigReader
from runconf_ui.interfaces.controller.application_controller import ShifterInterfaceState

from textual.app import App
import click
from rich import print

import os
from pathlib import Path
import logging
from datetime import datetime
import pkg_resources


class ShifterView(App):
    """
    Main app for the shifter view interface.
    """

    CSS_PATH = "shifter_view.tcss"
    BINDINGS = [("ctrl+q", "quit", "Quit")]

    def __init__(self, *args, **kwargs):
        """Constructor for the ShifterView class.
                args: default app args
        c
                kwargs:
                    - apparatus: str - The apparatus to use
                    - default_config: str - The default configuration file to use
                    - download_directory - default download directory
                    - session_name - tmux session name

                    - base_url- base url for the interface
                    - operation_url - operation url for the interface
        """
        super().__init__(*args)

        self._exit_message = ""
        # Read kwargs
        apparatus = kwargs.get("apparatus", os.environ.get("APPARATUS", "np02"))

        # messy...
        configuration = f"{Path(__file__).parent.absolute()}/../configuration/{apparatus}_configuration.yml"

        # Now we've done logs, we can read the configuration
        if Path(configuration).exists():
            interface_config = ShifterConfigReader(configuration, **kwargs)
        else:
            raise FileNotFoundError(f"Configuration file {configuration} not found")

        self.application_controller = ShifterInterfaceState(
            apparatus=apparatus,
            interface_config=interface_config,
            use_local=kwargs.get("use_local", False),
        )

        self._init_logger(kwargs.get("log_level", "INFO"))

    def _init_logger(self, log_level):
        # Grab from config reader

        logging_path = Path(
            f"{self.application_controller.interface_config.output_directory}/logs"
        )
        logging_path.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            filename=f"{logging_path}/shifter_view_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log",
            format="%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d:%H:%M:%S",
            level=log_level,
        )

        clean_old_files(logging_path, "log")

    def on_mount(self):
        """
        Mount App
        """
        self.theme = "catppuccin-latte"

        self.title = (
            f"Shifter Interface v{pkg_resources.get_distribution('runconf_ui').version}"
        )

        self.install_screen(
            ShifterViewScreen(self.application_controller),
            name="shifter_view_screen",
        )
        # Start with the SelectFileSessionScreen
        self.push_screen("shifter_view_screen")

    def action_quit(self):
        """Quit the application."""

        logging.info(self.screen.__class__)

        if isinstance(self.screen, QuitScreen):
            self.pop_screen()

        self.push_screen(
            QuitScreen(
                self.application_controller,
                classes="pop_up_screen",
            )
        )

    def exit(self, message) -> None:
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
    "-a",
    "--apparatus",
    "apparatus",
    required=False,
    default=os.getenv("APPARATUS"),
    help="set the detector apparatus i.e. NP02/NP04",
)
@click.option(
    "-s",
    "--shifter-interface-config",
    "default_config",
    required=False,
    help="Set default yaml config for this interface",
)
@click.option(
    "-d",
    "--daq-config-directory",
    "download_directory",
    required=False,
    help="Where do you want to download configs from/where are they located",
)
@click.option(
    "--session-name", "session_name", required=False, help="Name of daq session"
)
@click.option(
    "--base-url",
    "base_url",
    required=False,
    help="Base URL for the interface, not used for local operation",
)
@click.option(
    "--operation-url",
    "operation_url",
    required=False,
    help="Operation URL for the interface, not used for local operation",
)
@click.option(
    "--debug",
    "log_level",
    default="INFO",
    required=False,
    help="Set the debug log level",
)
@click.option(
    "-l",
    "--local-config",
    "use_local",
    required=False,
    is_flag=True,
    help="Use local config files instead of downloading from the github, expert use only!",
)
def main(
    apparatus,
    default_config,
    download_directory,
    session_name,
    base_url,
    operation_url,
    log_level,
    use_local,
):
    # Slghtly complicated here, as we need to remove unused args
    cli_args = {
        "apparatus": apparatus,
        "default_config": default_config,
        "download_directory": download_directory,
        "session_name": session_name,
        "base_url": base_url,
        "operation_url": operation_url,
        "log_level": log_level,
        "use_local": use_local,
    }

    cli_args = {k: v for k, v in cli_args.items() if v is not None}

    app = ShifterView(**cli_args)
    app.run()
    print(app.exit_message())


if __name__ == "__main__":
    main()
