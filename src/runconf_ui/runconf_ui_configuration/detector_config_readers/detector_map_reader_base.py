import logging
from abc import ABC, abstractmethod

from textual.widgets import Static, TabPane

from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)


class DetectorMapReaderBase(ABC):
    """
    Base class for detector map readers.
    This class defines the interface for reading detector maps.
    """

    def __init__(self, application_controller: ShifterInterfaceState) -> None:
        self._application_controller = application_controller
        logging.debug("Generating detector map...")

        full_opts = self.get_opts_from_controller()

        self._labels = [full_opts[k]["label"] for k in full_opts.keys()]
        self._panel_list = []

        for name, opts in full_opts.items():
            self.append_to_panel(name, opts)

    @abstractmethod
    def get_opts_from_controller(selfs) -> dict: ...

    @abstractmethod
    def append_to_panel(self, name: str, opts: dict) -> None:
        """
        Append a panel to the main container.
        This method should be implemented by subclasses to define how panels are added.
        """
        ...

    def initialise_system(self, panel_name: str, opts: dict, panel: Static) -> TabPane:
        """
        Initialise a system panel with the given options.
        """
        return TabPane(
            panel_name,
            panel,
            id=f"{opts.get('label', 'daq_system')}_tabs",
        )

    @property
    def panel_list(self):
        return self._panel_list

    @property
    def panel_labels(self):
        return self._labels
