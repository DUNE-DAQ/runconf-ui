"""
Main application for the shifter view interface.
"""

from cider.screens.shifter_view_screen import ShifterViewScreen
from cider.screens.quit_screen import QuitScreen
from cider.utils.file_cleaner import clean_old_files
from cider.utils.shifter_config_reader import ShifterConfigReader

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

    '''
    Need:
        - SESSION_FILE
        - CONFIG_DIR
        - SESSION_NAME
        
        - apparatus
        - base_url
        

    '''

    def __init__(self, *args, **kwargs):
        """Constructor for the ShifterView class.
        args: default app args
        
        kwargs:
            - apparatus: str - The apparatus to use
            - default_config: str - The default configuration file to use
            - download_directory - default download directory
            - session_name - tmux session name
            
            - base_url- base url for the interface
            - operation_url - operation url for the interface
        """
        super().__init__(*args)
        
        # Make the logging directory if it doesn't exist

        self._exit_message = ""

        # Read kwargs
        self._apparatus = kwargs.get("apparatus", os.environ.get("APPARATUS", "np02"))
        
        # messy...
        configuration = f"{Path(__file__).parent.absolute()}/../configuration/{self._apparatus}_configuration.yml"
        
        # Now we've done logs, we can read the configuration
        if Path(configuration).exists():
            self._interface_config = ShifterConfigReader(configuration, **kwargs)
        else:
            raise FileNotFoundError(f"Configuration file {configuration} not found")

        self.__init_logger(kwargs.get("log_level", "INFO"))        

    def __init_logger(self, log_level):
        # Grab from config reader
        
        
        logging_path = Path(f"{self._interface_config.output_directory}/logs")
        logging_path.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            filename=f"{logging_path}/shifter_view_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log",
            format="%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d:%H:%M:%S",
            level=log_level
        )

        clean_old_files(logging_path, "log")
        

    def on_mount(self):
        """
        Mount App
        """
        self.theme = "catppuccin-latte"

        self.title = f"Shifter Interface v{pkg_resources.get_distribution('cider').version}"

        self.install_screen(
            ShifterViewScreen(
                interface_config=self._interface_config,
            ),
            name="shifter_view_screen",
        )
        # Start with the SelectFileSessionScreen
        self.push_screen("shifter_view_screen")

    def action_quit(self):
        """Quit the application."""

        logging.info(self.screen.__class__)

        shifter_view = self.get_screen("shifter_view_screen")
        config, session = shifter_view.query_one(
            "#option_panel_main"
        ).get_config_session()

        if isinstance(self.screen, QuitScreen):
            self.pop_screen()

        self.push_screen(
            QuitScreen(
                session,
                config,
                classes="pop_up_screen",
            )
        )

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
@click.option("-a", "--apparatus", "apparatus", required=False, default=os.getenv("APPARATUS"))
@click.option("-d", "--default-config", "default_config", required=False)
@click.option("-o", "--download-directory", "download_directory", required=False)
@click.option("-s", "--session-name", "session_name", required=False)
@click.option("-b", "--base-url", "base_url", required=False)
@click.option("-p", "--operation-url", "operation_url", required=False)
@click.option("-l", "--log-level", "log_level", default="INFO", required=False)
def main(apparatus, default_config, download_directory, session_name, base_url, operation_url, log_level):    
    # Slghtly complicated here, as we need to remove unused args
    cli_args = {
        "apparatus": apparatus,
        "default_config": default_config,
        "download_directory": download_directory,
        "session_name": session_name,
        "base_url": base_url,
        "operation_url": operation_url,
        "log_level": log_level,
    }
    
    cli_args = {k: v for k, v in cli_args.items() if v is not None}
    
    app = ShifterView(**cli_args)
    app.run()
    print(app.exit_message())

if __name__ == "__main__":
    main()
