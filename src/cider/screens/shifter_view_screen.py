from textual.screen import Screen
from textual.containers import Grid
from textual.widgets import TabbedContent, TabPane, Header, Footer

from cider.widgets.detector_subsystem_panel import DetectorSubsystemPanel
from cider.widgets.options_panel import OptionPanel
from cider.widgets.file_io_panel import FileIOPanel



class ShifterViewScreen(Screen):
    def __init__(self, config_folder: str, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name, id, classes)

        self._config_folder = config_folder
    
    def compose(self):
        yield FileIOPanel(self._config_folder, id="file_io_panel")


        with TabbedContent(id="selection_tabs"):
            with TabPane("Detector Subsystem", id="detector_subsystem_tab"):
                yield DetectorSubsystemPanel(None, id="detector_subsystem_panel")
            with TabPane("Dataflow Apps", id="dataflow_apps_tab"):
                    yield DetectorSubsystemPanel(None, id="dataflow_apps_panel")
            with TabPane("Trigger", id="enable_trigger_tab"):
                    yield DetectorSubsystemPanel(None, id="enable_trigger_panel")


        yield OptionPanel(None, id="option_panel")
        
        yield Header()
        yield Footer()