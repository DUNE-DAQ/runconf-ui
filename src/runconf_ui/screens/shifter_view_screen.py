from textual.screen import Screen
from textual.containers import ScrollableContainer, Grid
from textual.widgets import TabbedContent, TabPane, Header, Footer, Static
from textual import on

from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)
from runconf_ui.runconf_ui_configuration.detector_config_readers.generate_enable_disable_map import (
    EnableDisableMapGen,
)
from runconf_ui.widgets.file_select_panel import FilePanelWidget
from runconf_ui.widgets.options_panel import OptionPanel
from runconf_ui.exceptions import CiderInvalidConfigurationException


import traceback
import logging
from runconf_ui.daq_config_interfaces.daq_config_file_io.buffer_file_manager import (
    BufferFileManager,
)
from runconf_ui.daq_config_interfaces.daq_tree_tools.daq_tree_manager import (
    DaqTreeManager,
)
from runconf_ui.screens.popup_manager import PopupManager
from runconf_ui.widgets.adjustable_attribute_panel import AdjustableAttributePanel
from runconf_ui.runconf_ui_configuration.detector_config_readers.generate_adjustable_attribute_map import (
    AdjustableAttributeMapGen,
)


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
        enable_disable_generator = EnableDisableMapGen(self._application_controller)
        adjustable_attribute_panel = AdjustableAttributeMapGen(
            self._application_controller
        )
        

        with ScrollableContainer(id="main_container"):
            yield FilePanelWidget(self._application_controller, classes="file_io_panel")

            with Grid(id="enable_disable_panel_container"):
                with TabbedContent(id="selection_tabs"):
                    for panel in enable_disable_generator.panel_list:
                        yield panel

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
                            for panel in enable_disable_generator.map_list:
                                if panel is not None:
                                    yield panel

                    with TabPane("Adjustable Rates", id="detector_map_tab"):
                        with TabbedContent(
                            "Attributes",
                            id="attribute_map_tabs",
                            classes="systematic_map_tabs multi_view_tabs",
                        ):

                            for panel in adjustable_attribute_panel.panel_list:
                                if panel is not None:
                                    yield panel

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
            self._load_new_configuration()
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
                f"[white]Invalid configuration[/white] [bold grey3]{self._application_controller.current_daq_config}:{self._application_controller.session_name}[/bold grey3] [white]passed, please check with the experts!"
            )
            logging.error(f"Error: {traceback.format_exc()}")

    @on(FilePanelWidget.FileNotFound)
    async def file_not_found(self, event: FilePanelWidget.FileNotFound):
        self.popups.show(
            f"[white]Configuration invalid or could not be opened: {event.file_path}",
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

    def _load_new_configuration(self):
        """Handle loading a new configuration file"""
        logging.info(
            f"Opening new file: {self._application_controller.session_name}:{self._application_controller.current_daq_config}"
        )

        self.file_service.load_configuration()
        self.query_one(OptionPanel).open_new_session()

        if not (
            self._application_controller.session_name
            and self._application_controller.buffer_daq_config
        ):
            logging.info("No session or configuration")
            return

        self._update_ui_after_config_load()

    def _update_ui_after_config_load(self):
        """Update UI components after loading a new configuration"""
        logging.debug("Updating enable/disable panels")
        for panel in self.query("EnableDisablePanel"):
            panel.open_new_session()
            panel.refresh(recompose=True)
            panel.update_button_styles()
            self._application_controller.current_state = {
                p.id: p.get_current_states() for p in self.query("EnableDisablePanel")
            }

        for panel in self.query("AdjustableAttributePanel"):
            panel.open_new_session()
            panel.refresh(recompose=True)
            self._application_controller.current_state = {
                p.id: p.get_current_states()
                for p in self.query("AdjustableAttributePanel")
            }

        self.tree_manager.update_all_trees(self)
        self.query_one("FilePanelWidget").update_file_info()

        self.popups.show(
            f"[white]Successfully opened new configuration[/white] [bold white]{self._application_controller.current_daq_config}",
            timer=5.0,
            success=True,
        )

    def on_enable_disable_panel_changed(self):
        """Handle changes in enable/disable panels"""
        self.tree_manager.update_all_trees(self)
