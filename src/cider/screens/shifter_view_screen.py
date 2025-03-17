from textual.screen import Screen
from textual.containers import ScrollableContainer, Grid
from textual.widgets import TabbedContent, TabPane, Header, Footer, Button, Static
from textual import on
from textual.css.query import NoMatches

from cider.widgets.multicomponent_panel import MultiComponentEnableDisablePanel
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.widgets.enable_disable_base import EnableDisablePanel
from cider.widgets.options_panel import OptionPanel
from cider.widgets.file_io_panel import FileIOPanel
from cider.utils.consolidate_file import ConsolidateFile
from cider.utils.daq_conf_tree import DaqConfTree
from cider.utils.shifter_config_reader import ShifterConfigReader

import traceback

from pathlib import Path
import os
import logging

from cider.widgets.popup_message import PopupMessage


class ShifterViewScreen(Screen):

    # Buffer config used to store the configuration during editing
    TMP_CONFIG = Path(f"/tmp/shifter_configs-{os.getlogin()}/tmp_config.data.xml")

    changed_session = False

    """
    Main shifter view, thid is the main screen that the shifter will see
    """

    def __init__(
        self,
        output_directory: str,
        interface_config: str = "../configuration/np02_configuration.yml",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)

        logging.info("Opening shifter view screen")

        self._config = ShifterConfigReader(interface_config)

        self._output_directory = output_directory

        self._configuration = None
        self._session = None

    def compose(self):
        """
        Generate the screen layout
        """

        with ScrollableContainer(id="main_container"):

            # File dropdowns
            yield FileIOPanel(
                self._config.default_config,
                self._config.install_path,
                id="file_io_panel",
            )

            # Grid containing buttons AND maps
            with Grid(id="enable_disable_panel_container"):

                # Get the tabs with buttons, these are all set up in the config file
                with TabbedContent(id="selection_tabs"):
                    for panel in self._config.panel_list:
                        yield panel

                # All maps
                with TabbedContent(
                    "SystematicMap",
                    id="systematic_map_tabs",
                    classes="systematic_map_tabs",
                ):
                    # Full system view, this is always present and doesn't need configurating
                    with TabPane("System View", id="full_system_map_tab"):
                        yield ScrollableContainer(
                            Static(
                                DaqConfTree(None, None).print_tree(),
                                id="tree_view_full",
                            ),
                            id="tree_view_full_container",
                            classes="tree_view_full_container",
                        )

                    # For all other maps, we need to loop over the config file. Maps display ONLY for
                    # mutlisystem systems
                    for panel in self._config.map_list:
                        yield panel

            # help/create/quit/etc.
            yield OptionPanel(
                None,
                None,
                self._output_directory,
                id="option_panel_main",
                classes="options_panel",
            )

        # Just nice
        yield Header()
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed):
        """
        Handle button press events.
        """
        if event.button.id == "open_file_button":
            try:
                self.open_new_file()
            except RuntimeError as e:
                # Display the error message in a pop-up
                self.show_popup(
                    f"[white]Invalid configuration[/white] [bold grey3]{self.query_one(FileIOPanel).selected_config_name}:{self.query_one(FileIOPanel).selected_session_name}[/bold grey3] [white]passed, please check with the experts!\n\
                    Log saved to[/white] [bold grey3]{logging.getLogger().handlers[0].baseFilename}[/bold grey3]"
                )
                # Optionally log the error for debugging
                logging.error(
                    f"Couldn't open file: {self.query_one(FileIOPanel).selected_config_name}:{self.query_one(FileIOPanel).selected_session_name}"
                )
                logging.error(f"Error: {e}")
                await self.deconfigure()
            except Exception as e:
                self.show_popup(
                    f"[white]ERROR::{e}. This is likely an issue with the interface. Please check with the experts!\nLog saved to[/white] [bold grey3]{logging.getLogger().handlers[0].baseFilename}[/bold grey3]"
                )
                # Optionally log the error for debugging
                logging.error(
                    f"Couldn't open file: {self.query_one(FileIOPanel).selected_config_name}:{self.query_one(FileIOPanel).selected_session_name}"
                )
                logging.error(f"{traceback.format_exc()}")
                await self.deconfigure()

    def show_popup(self, message: str, timer: float = 10.0):
        """
        Display a pop-up message on the screen.
        """
        # Remove any existing pop-up to avoid duplicates
        self.remove_popup()

        # Create and mount the pop-up
        popup = PopupMessage(message, timer, classes="popup popup_failure")
        self.query_one("#main_container").mount(popup)

    def remove_popup(self):
        """
        Remove any existing pop-up from the screen.
        """
        try:
            # Find and remove any existing pop-up
            existing_popup = self.query_one(".popup", expect_type=PopupMessage)
            existing_popup.remove()
        except NoMatches:
            # No pop-up to remove
            pass

    @on(FileIOPanel.Deconfigured)
    async def deconfigure(self):
        self.query_one(OptionPanel).open_new_session(None, None)
        for a in self.query("EnableDisablePanel"):
            a.open_new_session(None, None)
            a.refresh(recompose=True)

    @on(FileIOPanel.PathChanged)
    async def on_path_changed(self):
        try:
            # Open new file
            self.open_new_file()
        except Exception as _:
            # Unload config
            await self.deconfigure()
            # Lives at the bottom of the screen
            self.show_popup("[white]Configuration has been removed from disk!")

    @on(FileIOPanel.FileNotFound)
    async def file_not_found(self, event: FileIOPanel.FileNotFound):
        self.show_popup(
            f"[white]Configuration file not found: {event.file_path}\nLog saved to[/white] [bold grey3]{logging.getLogger().handlers[0].baseFilename}[/bold grey3]",
            timer=10.0,
        )
        
    @on(EnableDisablePanel.TooManyPresses)
    async def too_many_presses(self, event: EnableDisablePanel.TooManyPresses):
        self.show_popup(
            f"[white]{event.message()}",
            timer=3.0
        )
    def open_new_file(self):
        """
        Open a new file is the only cross-app interface
        """
        # Grab session + config from file selector
        session_name = self.query_one(FileIOPanel).selected_session_name
        original_configuration = self.query_one(FileIOPanel).selected_config_name

        logging.info(f"Opening new file: {session_name}:{original_configuration}")

        # Make directories
        self.TMP_CONFIG.parent.mkdir(parents=True, exist_ok=True)

        # Now we make a temporary copy of the configuration object
        # For ease of copying we copy the entire session into a single file
        ConsolidateFile(
            original_configuration, session_name, "Session", str(self.TMP_CONFIG)
        )()
        logging.info("Configuration copied to temporary file")

        # Get configuration
        buffer_config = ConfigurationWrapper(str(self.TMP_CONFIG))

        # Open new session
        self.query_one(OptionPanel).open_new_session(buffer_config, session_name)

        if not session_name or not buffer_config:
            logging.info("No session or configuration")
            pass

        self._configuration = buffer_config
        self._session = session_name

        logging.debug("Updating enable/disable panels")
        # Update all panels
        for a in self.query("EnableDisablePanel"):
            a.open_new_session(buffer_config, session_name)
            a.refresh(recompose=True)
            a.update_button_styles()

        # Update trees
        self.update_trees(buffer_config, session_name)

    def on_enable_disable_panel_changed(self, message: EnableDisablePanel.Changed):
        # Change from enable->disable or vice versa
        self.update_trees(message.configuration, message.session)

    def update_trees(self, configuration: ConfigurationWrapper, session: str):
        # We get the the full system first
        main_tree = DaqConfTree(configuration, session)

        # Update the static panel
        self.query_one("#tree_view_full").update(main_tree.print_tree())
        # Tree also tells us exactly what's on/off
        disabled = main_tree.disabled_objs

        # Update component level trees
        for panel in self.query("EnableDisablePanel"):
            if isinstance(panel, MultiComponentEnableDisablePanel):
                panel.update_disabled(disabled)
                self.update_tree(panel)
            # Have to do this twice to get the correct state
            panel.update_button_styles()
    

    def update_tree(self, panel: MultiComponentEnableDisablePanel):
        # Get current state of panel
        self.query_one(f"#tree_view_{panel.id.replace('_subsystem_panel', '')}").update(
            panel.get_tree().print_tree()
        )
