from textual.screen import Screen
from textual.containers import Grid
from textual.widgets import TabbedContent, TabPane, Header, Footer, Button
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper


from cider.widgets.single_component_panel import SingleComponentEnableDisablePanel
from cider.widgets.multicomponent_panel import MultiComponentEnableDisablePanel
from cider.widgets.trigger_panel import TriggerPanel
from cider.widgets.options_panel import OptionPanel
from cider.widgets.file_io_panel import FileIOPanel
from cider.utils.consolidate_file import ConsolidateFile

from pathlib import Path
import os
import yaml


class ShifterViewScreen(Screen):

    TMP_CONFIG = Path(f"/tmp/shifter_configs-{os.getlogin()}/tmp_config.data.xml")

    changed_session = False

    '''
    Main shifter view, thid is the main screen that the shifter will see
    '''

    def __init__(
        self,
        config_folder: str,
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

    def compose(self):
        '''
        Generate the screen layout
        '''
        yield FileIOPanel(self._config_folder, id="file_io_panel")

        with TabbedContent(id="selection_tabs"):
            with TabPane("Detector Subsystem", id="detector_subsystem_tab"):
                yield MultiComponentEnableDisablePanel(
                    None, None, self.detector_system_map, id="detector_subsystem_panel"
                )
            with TabPane("Dataflow Apps", id="dataflow_apps_tab"):
                yield SingleComponentEnableDisablePanel(
                    None, None, ["DFApplication"], id="dataflow_subsystem_panel"
                )
            with TabPane("Trigger", id="enable_trigger_tab"):
                yield TriggerPanel(None, None, self.trigger_map, id="trigger_panel")

        yield OptionPanel(None, "", id="option_panel")

        yield Header()
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed):
        '''
        For simplicity this button's functionality is accessible at the screen level
        '''
        if event.button.id == "open_file_button":
            try:
                self.open_new_file()
            except Exception as e:
                raise e

    def open_new_file(self):
        '''
        Open a new file is the only cross-app interface
        '''
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
            return

        for a in self.query("__EnableDisablePanel"):
            a.open_new_session(buffer_config, session_name)
