from textual.screen import Screen
from textual.containers import ScrollableContainer, Grid
from textual.widgets import TabbedContent, TabPane, Header, Footer, Static
from textual import on
from textual.css.query import NoMatches
from textual.message import Message

from runconf_ui.widgets.multicomponent_panel import MultiComponentEnableDisablePanel
from runconf_ui.interfaces.controller.daq_conf_wrapper import DaqConfigurationWrapper
from runconf_ui.widgets.options_panel import OptionPanel
from runconf_ui.widgets.file_select_panel import FilePanelWidget
from runconf_ui.utils.daq_conf_tools.consolidate_daq_conf import ConsolidateDAQConf
from runconf_ui.utils.daq_conf_tools.daq_conf_tree import DaqConfTree
from runconf_ui.interfaces.controller.application_controller import (
    ShifterInterfaceState,
)
from runconf_ui.utils.daq_conf_tools.generate_enable_disable_map import EnableDisableMapGen
from runconf_ui.widgets.popup_message import PopupMessage

import traceback
from pathlib import Path
import os
import logging


class ShifterViewScreen(Screen):
    # If we're in a tmux session we can get the id
    buffer_id = os.environ.get("SESSION_NAME", os.getlogin())

    # Buffer config used to store the configuration during editing
    TMP_CONFIG = Path(f"/tmp/shifter_configs-{buffer_id}/tmp_config.data.xml")

    changed_session = False

    """
    Main shifter view, thid is the main screen that the shifter will see
    """

    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)

        logging.info("Opening shifter view screen")

        self._application_controller = application_controller

    def compose(self):
        """
        Generate the screen layout
        """
        enable_disable_generator = EnableDisableMapGen(self._application_controller)

        with ScrollableContainer(id="main_container"):
            # File dropdowns
            yield FilePanelWidget(self._application_controller, classes="file_io_panel")

            # Grid containing buttons AND maps
            with Grid(id="enable_disable_panel_container"):

                # Get the tabs with buttons, these are all set up in the config file
                with TabbedContent(id="selection_tabs"):
                    for panel in enable_disable_generator.panel_list:
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
                                DaqConfTree(self._application_controller).print_tree(),
                                id="tree_view_full",
                            ),
                            id="tree_view_full_container",
                            classes="tree_view_full_container",
                        )

                    # For all other maps, we need to loop over the config file. Maps display ONLY for
                    # mutlisystem systems
                    for panel in enable_disable_generator.map_list:
                        yield panel

            # help/create/quit/etc.
            yield OptionPanel(
                application_controller=self._application_controller,
                id="option_panel_main",
                classes="options_panel",
            )

        # Just nice
        yield Header()
        yield Footer()

    @on(FilePanelWidget.FileSelected)
    async def select_new_file(self):
        """
        Handle button press events.
        """
        try:
            self.open_new_file()
        except Exception:
            # Display the error message in a pop-up
            self.show_popup(
                f"[white]Invalid configuration[/white] [bold grey3]{self._application_controller.current_daq_config}:{self._application_controller.session_name}[/bold grey3] [white]passed, please check with the experts!"
            )
            # Optionally log the error for debugging
            logging.error(f"Error: {traceback.format_exc()}")

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

    @on(FilePanelWidget.FileNotFound)
    async def file_not_found(self, event: FilePanelWidget.FileNotFound):
        self.show_popup(
            f"[white]Configuration invalid or could not be opened: {event.file_path}",
            timer=10.0,
        )

    def open_new_file(self):
        """
        Open a new file is the only cross-app interface
        """
        # Grab session + config from file selector
        logging.info(
            f"Opening new file: {self._application_controller.session_name}:{self._application_controller.current_daq_config}"
        )

        # Make directories
        self.TMP_CONFIG.parent.mkdir(parents=True, exist_ok=True)

        # Now we make a temporary copy of the configuration object
        # For ease of copying we copy the entire session into a single file
        logging.info(f"Session name {self._application_controller.session_name}")
        try:
            ConsolidateDAQConf(
                self._application_controller.current_daq_config,
                self._application_controller.session_name,
                "Session",
                str(self.TMP_CONFIG),
            )()
            logging.info("Configuration copied to temporary file")
        except Exception as e:
            logging.error(f"Error copying configuration: {e}")
            logging.error(traceback.format_exc())
            raise e

        # Get configuration
        self._application_controller.buffer_daq_config = DaqConfigurationWrapper(
            str(self.TMP_CONFIG)
        )

        # Open new session
        self.query_one(OptionPanel).open_new_session()

        if (
            not self._application_controller.session_name
            or not self._application_controller.buffer_daq_config
        ):
            logging.info("No session or configuration")
            return

        logging.debug("Updating enable/disable panels")
        # Update all panels
        for a in self.query("EnableDisablePanel"):
            a.open_new_session()
            a.refresh(recompose=True)
            a.update_button_styles()
            self._application_controller.current_state = {
                a.id: a.get_current_states() for a in self.query("EnableDisablePanel")
            }         

        # Update trees
        self.update_trees()
        
        
        self.query_one("FilePanelWidget").update_file_info()

    def on_enable_disable_panel_changed(self):
        # Change from enable->disable or vice versa
        self.update_trees()


    def update_trees(self):
        # We get the the full system first
        main_tree = DaqConfTree(self._application_controller)
        # Update the static panel
        self.query_one("#tree_view_full").update(main_tree.print_tree())
        # Tree also tells us exactly what's on/off
        disabled = main_tree.disabled_objs
        logging.info(f"Disabled objects: {disabled}")

        # Update component level trees
        for panel in self.query("EnableDisablePanel"):
            self._application_controller.current_state[panel.id] = panel.get_current_states()

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

