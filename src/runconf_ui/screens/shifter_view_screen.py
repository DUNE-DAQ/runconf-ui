import logging
import traceback

from textual import on
from textual.containers import Grid, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, TabbedContent, TabPane

from runconf_ui.daq_config_interfaces.daq_config_file_io.buffer_file_manager import (
    BufferFileManager,
)
from runconf_ui.daq_config_interfaces.daq_tree_tools.daq_tree_manager import (
    DaqTreeManager,
)
from runconf_ui.exceptions import CiderInvalidConfigurationException
from runconf_ui.runconf_ui_configuration.detector_config_readers.generate_adjustable_attribute_map import (
    AdjustableAttributeMapGen,
)
from runconf_ui.runconf_ui_configuration.detector_config_readers.generate_enable_disable_map import (
    EnableDisableMapGen,
)
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)
from runconf_ui.screens.popup_manager import PopupManager
from runconf_ui.widgets.adjustable_attribute_panel import AdjustableAttributePanel
from runconf_ui.widgets.enable_disable_base import EnableDisablePanel
from runconf_ui.widgets.file_select_panel import FilePanelWidget
from runconf_ui.widgets.options_panel import OptionPanel


class ShifterViewScreen(Screen):
    """Main shifter view, this is the main screen that the shifter will see"""

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
        self.file_service = BufferFileManager(application_controller)
        self.popups = PopupManager(self)
        self.tree_manager = DaqTreeManager(application_controller)

    def compose(self):
        """Generate the screen layout"""
        # Do not generate detector-dependent panels here. Create placeholder
        # containers which will be populated after a detector configuration is
        # loaded. This avoids requiring a detector config to exist at
        # compose-time.
        with ScrollableContainer(id="main_container"):
            yield FilePanelWidget(self._application_controller, classes="file_io_panel")

            with Grid(id="enable_disable_panel_container"):
                # selection tabs placeholder - enable/disable panels will be
                # mounted here after a config is loaded. Provide an empty
                # TabPane so Textual doesn't attempt to wrap a `None` child.
                with TabbedContent(id="selection_tabs"):
                    with TabPane("Selection", id="selection_tab_placeholder"):
                        yield Static("", id="selection_tab_placeholder_static")

                with TabbedContent(
                    "Map Views",
                    id="multi_view_tabs",
                    classes="multi_view_tabs",
                ):
                    with TabPane("System Maps", id="enable_disable_map_tab"):
                        with TabbedContent(
                            "SystematicMap",
                            id="systematic_map_tabs",
                            classes="systematic_map_tabs",
                        ):
                            with TabPane("System View", id="full_system_map_tab"):
                                yield ScrollableContainer(
                                    Static("", id="tree_view_full"),
                                    id="tree_view_full_container",
                                    classes="tree_view_full_container",
                                )
                            # map panels will be mounted into systematic_map_tabs

                    with TabPane("Adjustable Rates", id="detector_map_tab"):
                        with TabbedContent(
                            "Attributes",
                            id="attribute_map_tabs",
                            classes="systematic_map_tabs multi_view_tabs",
                        ):
                            # attribute panels will be mounted into attribute_map_tabs
                            with TabPane("Attributes", id="attribute_tab_placeholder"):
                                yield Static("", id="attribute_tab_placeholder_static")

            yield OptionPanel(
                application_controller=self._application_controller,
                id="option_panel_main",
                classes="options_panel",
            )

        yield Header()
        yield Footer()

    @on(OptionPanel.ResetPressed)
    @on(FilePanelWidget.FileSelected)
    async def select_new_file(self):
        """Handle new file selection"""
        try:
            await self._load_new_configuration()
        except CiderInvalidConfigurationException:
            self.popups.show(
                f"[white]Invalid configuration[/white] [bold grey3]{self._application_controller.shifter_interface_config} set up incorrectly!"
            )
            logging.error(f"Error: {traceback.format_exc()}")

        except Exception:
            if (
                self._application_controller.session_name is None
                or self._application_controller.current_daq_config is None
            ):
                self.popups.show(
                    "[white]No configuration can be selected, please make sure you're using a compatible DAQ version[/white]"
                )

            self.popups.show(
                f"[white]Invalid configuration[/white] [bold grey3]{self._application_controller.current_daq_config} passed. please check with the experts! This is likely a daq-software/configuration version mismatch or a corrupted file."
            )
            logging.error(f"Error: {traceback.format_exc()}")

    @on(FilePanelWidget.FileNotFound)
    async def file_not_found(self, event: FilePanelWidget.FileNotFound):
        if event.msg is None:
            event_msg = f"[white]Configuration invalid or could not be opened: {event.file_path}"
        else:
            event_msg = f"[white]{event.msg} (Cannot open configuration {event.file_path})"

        
        self.popups.show(
            event_msg,
            timer=10.0,
        )

    @on(FilePanelWidget.RepoCorrupted)
    async def repo_corrupted(self):
        self.popups.show(
            "[white]Configuration git repo corrupted, resetting", timer=10.0
        )

    @on(AdjustableAttributePanel.AttributeOutOfBounds)
    async def attribute_out_of_bounds(
        self, event: AdjustableAttributePanel.AttributeOutOfBounds
    ):
        """Handle out of bounds attribute values"""
        self.popups.show(
            f"[white]{event.message}",
            timer=5.0,
        )

    async def _load_new_configuration(self):
        """Handle loading a new configuration file."""
        logging.info(
            f"Opening new file: {self._application_controller.session_name}:{self._application_controller.current_daq_config}"
        )

        # load configuration 
        self.file_service.load_configuration()
        # update option panel UI
        self.query_one(OptionPanel).open_new_session()

        if not (
            self._application_controller.session_name
            and self._application_controller.buffer_daq_config
        ):
            logging.info("No session or configuration")
            return

        await self._update_ui_after_config_load()

    async def _update_ui_after_config_load(self):
        """Update UI components after loading a new configuration.

        This generates detector-dependent panels and mounts them into the
        placeholder containers created during compose().
        """
        logging.debug("Generating and mounting enable/disable & attribute panels")

        # instantiate generators now that the detector config is available
        enable_disable_generator = EnableDisableMapGen(self._application_controller)
        adjustable_attribute_panel = AdjustableAttributeMapGen(
            self._application_controller
        )

        # locate placeholder containers by id
        selection_tabs = self.query_one("#selection_tabs", TabbedContent)
        systematic_map_tabs = self.query_one(
            "#systematic_map_tabs", TabbedContent
        )
        attribute_map_tabs = self.query_one("#attribute_map_tabs", TabbedContent)

        # remove any previously mounted generator panels to avoid duplicates
        # on reload. We remove by id to avoid removing built-in placeholder
        # panes (for example the 'full_system_map_tab' that contains the
        # main tree view).
        for panel_tab in enable_disable_generator.panel_list:
            if panel_tab is None:
                continue
            try:
                # Use TabbedContent.remove_pane to remove both the Tab and the pane
                await selection_tabs.remove_pane(panel_tab.id)
            except Exception:
                pass

        for map_tab in enable_disable_generator.map_list:
            if map_tab is None:
                continue
            try:
                await systematic_map_tabs.remove_pane(map_tab.id)
            except Exception:
                pass

        for attr_tab in adjustable_attribute_panel.panel_list:
            if attr_tab is None:
                continue
            try:
                await attribute_map_tabs.remove_pane(attr_tab.id)
            except Exception:
                pass

        # mount selection panels. The generators return TabPane objects; mount
        # them directly into the `selection_tabs` container so TabbedContent
        # creates tab entries accordingly.
        for panel_tab in enable_disable_generator.panel_list:
            if panel_tab is None:
                continue
            
            await selection_tabs.add_pane(panel_tab)

        # remove the placeholder selection tab if it exists now we've added real panes
        try:
            await selection_tabs.remove_pane("selection_tab_placeholder")
        except Exception:
            pass

        # mount map views (TabPane objects)
        for map_tab in enable_disable_generator.map_list:
            if map_tab is None:
                continue

            await systematic_map_tabs.add_pane(map_tab)

            # Debug: list children of the newly added pane and check for expected tree Static
            try:
                # expected tree static id uses label: derive label from panel id patterns
                label = map_tab.id.replace("_tabs", "")
                expected_tree_id = f"tree_view_{label}"
                try:
                    self.query_one(f"#{expected_tree_id}")
                except Exception:
                    pass
            except Exception:
                pass

        # mount adjustable attribute panels (TabPane objects)
        for attr_tab in adjustable_attribute_panel.panel_list:
            if attr_tab is None:
                continue

            await attribute_map_tabs.add_pane(attr_tab)

        # now refresh panels and update controller state
        for panel in self.query(EnableDisablePanel):
            panel.open_new_session()
            panel.refresh(recompose=True)
            panel.update_button_styles()
            self._application_controller.current_state = {
                p.id: p.get_current_states() for p in self.query(EnableDisablePanel)
            }

        for panel in self.query(AdjustableAttributePanel):
            panel.open_new_session()
            panel.refresh(recompose=True)
            self._application_controller.current_state = {
                p.id: p.get_current_states()
                for p in self.query(AdjustableAttributePanel)
            }

        self.tree_manager.update_all_trees(self)

        self.query_one(FilePanelWidget).update_file_info()

        self.popups.show(
            f"[white]Successfully opened new configuration[/white] [bold white]{self._application_controller.current_daq_config}",
            timer=5.0,
            success=True,
        )



    def on_enable_disable_panel_changed(self):
        """Handle changes in enable/disable panels"""        
        self.tree_manager.update_all_trees(self)
