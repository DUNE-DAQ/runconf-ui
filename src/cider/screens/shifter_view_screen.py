from textual.screen import Screen
from textual.containers import ScrollableContainer, Grid, Container
from textual.widgets import TabbedContent, TabPane, Header, Footer, Button, Static
from textual import on
from textual.css.query import NoMatches
from textual.reactive import reactive


from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.widgets.single_component_panel import SingleComponentEnableDisablePanel
from cider.widgets.multicomponent_panel import MultiComponentEnableDisablePanel
from cider.widgets.enable_disable_base import EnableDisablePanel
from cider.widgets.options_panel import OptionPanel
from cider.widgets.file_io_panel import FileIOPanel
from cider.utils.consolidate_file import ConsolidateFile
from cider.utils.daq_conf_tree import DaqConfTree, ComponentLevelTree


from pathlib import Path
import os
import yaml


class PopupMessage(Static):
    """A custom widget for displaying pop-up messages."""

    def on_mount(self):
        # Automatically remove the pop-up after 3 seconds
        self.set_timer(10.0, self.remove_popup)

    def remove_popup(self):
        """Remove the pop-up from the DOM."""
        self.remove()


class ShifterViewScreen(Screen):

    TMP_CONFIG = Path(f"/tmp/shifter_configs-{os.getlogin()}/tmp_config.data.xml")

    changed_session = False
    show_popup = reactive(False)

    """
    Main shifter view, thid is the main screen that the shifter will see
    """

    def __init__(
        self,
        config_folder: str,
        output_directory: str,
        interface_config: str = "../configuration/np02_configuration.yml",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)

        with open(interface_config, "r") as f:
            interface_conf_file = yaml.safe_load(f)

            self.detector_system_map = interface_conf_file["DetectorSystemMap"]
            self.trigger_map = interface_conf_file["TriggerMap"]

        self._config_folder = config_folder
        self._output_directory = output_directory

    def compose(self):
        """
        Generate the screen layout
        """
        with ScrollableContainer(id="main_container"):
            yield FileIOPanel(self._config_folder, id="file_io_panel")

            with Grid(id="enable_disable_panel_container"):
                with TabbedContent(id="selection_tabs"):
                    with TabPane("Detector Component", id="detector_subsystem_tab"):
                        yield MultiComponentEnableDisablePanel(
                            None,
                            None,
                            self.detector_system_map,
                            id="detector_subsystem_panel",
                            classes="detector_subsystem",
                        )
                    with TabPane("Dataflow", id="dataflow_apps_tab"):
                        yield SingleComponentEnableDisablePanel(
                            None,
                            None,
                            ["DFApplication"],
                            id="dataflow_subsystem_panel",
                            classes="detector_subsystem",
                        )
                    with TabPane("Trigger", id="enable_trigger_tab"):
                        yield MultiComponentEnableDisablePanel(
                            None,
                            None,
                            self.trigger_map,
                            id="trigger_panel",
                            classes="detector_subsystem",
                        )
                with TabbedContent(
                    "SystematicMap",
                    id="systematic_map_tabs",
                    classes="systematic_map_tabs",
                ):
                    with TabPane("Detector View", id="full_system_map_tab"):
                        yield ScrollableContainer(
                            Static(
                                DaqConfTree(None, None).print_tree(),
                                id="tree_view_full",
                            ),
                            id="tree_view_full_container",
                            classes="tree_view_full_container",
                        )
                    with TabPane("Trigger View", id="trigger_system_tab"):
                        yield ScrollableContainer(
                            Static(
                                ComponentLevelTree(
                                    None, None, self.trigger_map
                                ).print_tree(),
                                id="tree_view_trigger",
                            ),
                            id="tree_view_trigger_container",
                        )

            yield OptionPanel(
                None,
                None,
                self._output_directory,
                id="option_panel_main",
                classes="options_panel",
            )

        yield Header()
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed):
        """
        Handle button press events.
        """
        if event.button.id == "open_file_button":
            try:
                self.open_new_file()
            except Exception as e:
                # Display the error message in a pop-up
                self.show_popup(
                    f"[white]Invalid configuration[/white] [bold grey3]{self.query_one(FileIOPanel).selected_config_name}:{self.query_one(FileIOPanel).selected_session_name}[/bold grey3] [white]passed, please check with the experts!"
                )
                # Optionally log the error for debugging
                self.log.error(f"Error opening file: {e}")

    def show_popup(self, message: str):
        """
        Display a pop-up message on the screen.
        """
        # Remove any existing pop-up to avoid duplicates
        self.remove_popup()

        # Create and mount the pop-up
        popup = PopupMessage(message, classes="popup")
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
    def deconfigure(self):
        self.query_one(OptionPanel).open_new_session(None, None)
        for a in self.query("EnableDisablePanel"):
            a.open_new_session(None, None)
            a.refresh(recompose=True)

    def open_new_file(self):
        """
        Open a new file is the only cross-app interface
        """
        session_name = self.query_one(FileIOPanel).selected_session_name
        original_configuration = self.query_one(FileIOPanel).selected_config_name

        self.TMP_CONFIG.parent.mkdir(parents=True, exist_ok=True)

        # Now we make a temporary copy of the configuration object
        ConsolidateFile(
            original_configuration, session_name, "Session", str(self.TMP_CONFIG)
        )()

        # Get configuration
        buffer_config = ConfigurationWrapper(str(self.TMP_CONFIG))

        self.query_one(OptionPanel).open_new_session(buffer_config, session_name)

        if not session_name or not buffer_config:
            pass

        for a in self.query("EnableDisablePanel"):
            a.open_new_session(buffer_config, session_name)
            a.refresh(recompose=True)

        # Update trees
        self.update_trees(buffer_config, session_name)

    def on_enable_disable_panel_changed(self, message: EnableDisablePanel.Changed):
        for a in self.query("EnableDisablePanel"):
            a.refresh(recompose=True)

        self.update_trees(message.configuration, message.session)

    def update_trees(self, configuration: ConfigurationWrapper, session: str):
        main_tree = DaqConfTree(configuration, session)
        self.query_one("#tree_view_full").update(main_tree.print_tree())
        # For trigger info we need to hack
        disabled = main_tree.disabled_objs
        # We also want trigger states
        trigger_states = self.query_one("#trigger_panel").get_full_state_info()

        trigger_tree = ComponentLevelTree(
            configuration, session, trigger_states, disabled
        )

        self.query_one("#tree_view_trigger").update(trigger_tree.print_tree())
