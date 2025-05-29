from runconf_ui.widgets.multicomponent_panel import MultiComponentEnableDisablePanel
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)

from textual.widgets import TabPane, Static
from textual.containers import ScrollableContainer

import logging


class EnableDisableMapGen:
    def __init__(self, application_controller: ShifterInterfaceState) -> None:
        self._application_controller = application_controller
        logging.debug("Generating enable/disable map...")
        self._panel_list, self._map_list, self._panel_labels = self.read_panel_options()

    def read_panel_options(self):
        # Grab all panels we specify in the YAML
        panel_opts = self._application_controller.shifter_interface_config.panel_options

        logging.debug(f"Panel options: {panel_opts}")

        # To be filled with panels
        panel_list = []

        # for multi system panels we also generate a map
        map_list = []
        panel_labels = [panel_opts[k]["label"] for k in panel_opts.keys()]

        for panel_name, opts in panel_opts.items():
            panel, map = self._parse_options(panel_name, opts)
            if panel is None:
                logging.warning(
                    f"Panel {panel_name} could not be created with options {opts}"
                )
                continue

            panel_list.append(panel)

            if map is not None:
                map_list.append(map)

        return panel_list, map_list, panel_labels

    def _parse_options(self, panel_name: str, opts: dict):
        return self.initialise_multi_system(panel_name, opts)

    def _initalise_system(self, panel_name, opts, panel):
        return TabPane(
            panel_name,
            panel,
            id=f"{opts.get('label', 'daq_system')}_tabs",
        )

    def initialise_multi_system(self, panel_name, opts):
        panel = MultiComponentEnableDisablePanel(
            self._application_controller,
            opts,
            id=f"{opts.get('label', 'MultiSystem')}_subsystem_panel",
            classes="detector_subsystem",
        )

        panel_tab = self._initalise_system(panel_name, opts, panel)

        map = ScrollableContainer(
            Static(
                panel.get_tree().print_tree(),
                id=f"tree_view_{opts.get('label', 'MultiSystem')}",
            ),
            id=f"{opts.get('label', 'MultiSystem')}_view_container",
        )

        map_tab = self._initalise_system(opts.get("view_panel", ""), opts, map)

        return panel_tab, map_tab

    @property
    def panel_list(self):
        return self._panel_list

    @property
    def map_list(self):
        return self._map_list

    @property
    def panel_labels(self):
        return self._panel_labels
