from cider.interfaces.controller.config_wrapper import ConfigurationWrapper

from textual.visual import SupportsVisual
from textual.widgets import Static, Placeholder
from textual.containers import Grid

class DetectorSubsystemPanel(Static):
    def __init__(self, configuration: ConfigurationWrapper | None, content: str | SupportsVisual = "", *, expand: bool = False, shrink: bool = False, markup: bool = True, name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False) -> None:
        super().__init__(content, expand=expand, shrink=shrink, markup=markup, name=name, id=id, classes=classes, disabled=disabled)

        self._configuration = configuration

    @property
    def configuration(self)->ConfigurationWrapper | None:
        return self._configuration
    
    @configuration.setter
    def configuration(self, configuration: ConfigurationWrapper | None):
        self._configuration = configuration
        self.refresh()
    
    def compose(self):
        with Grid(id="detector_subsystem_panel_grid"):
            yield Placeholder("Buttons Panel", id="buttons_panel")
            yield Placeholder("Schematic View", id="schematic_view")