from cider.widgets.single_component_panel import SingleComponentEnableDisablePanel
from cider.widgets.multicomponent_panel import MultiComponentEnableDisablePanel
from cider.utils.daq_conf_tree import ComponentLevelTree

from textual.widgets import TabPane, Static
from textual.containers import ScrollableContainer

import yaml


# Class for reading a YAML config and producing panels
class ShifterConfigReader:
    def __init__(self, config_file):

        with open(config_file, "r") as f:
            self._config = yaml.safe_load(f)

        # We can get settings
        general_settings = self._config.get("General", {})

        # Default config file
        self._default_config = general_settings.get("default_config", None)

        self._panel_list, self._map_list, self._panel_labels = self.read_panel_options()

    @property
    def default_config(self):
        return self._default_config

    @property
    def panel_list(self):
        return self._panel_list

    @property
    def map_list(self):
        return self._map_list

    @property
    def panel_labels(self):
        return self._panel_labels

    def read_panel_options(self):
        # Grab all panels we specify in the YAML
        panel_opts = self._config.get("PanelOptions", {})

        # To be filled with panels
        panel_list = []

        # for multi system panels we also generate a map
        map_list = []
        panel_labels = [panel_opts[k]["label"] for k in panel_opts.keys()]

        for panel_name, opts in panel_opts.items():
            if opts.get("panel_type", None) == "singlesystem":
                panel_list.append(self.initialise_single_system(panel_name, opts))
            elif opts.get("panel_type", None) == "multisystem":
                p, m = self.initialise_multi_system(panel_name, opts)
                panel_list.append(p)
                map_list.append(m)
            else:
                raise ValueError(f"Unknown panel type {opts.get('panel_type')}")

        return panel_list, map_list, panel_labels

    def _initalise_system(self, panel_name, opts, panel):
        return TabPane(
            panel_name,
            panel,
            id=f"{opts.get('label', 'daq_system')}_tabs",
        )

    def initialise_single_system(self, panel_name, opts):
        panel = SingleComponentEnableDisablePanel(
            None,
            None,
            opts.get("classes", []),
            id=f"{opts.get('label', 'SingleSystem')}_subsystem_panel",
            classes="detector_subsystem",
        )

        return self._initalise_system(panel_name, opts, panel)

    def initialise_multi_system(self, panel_name, opts):
        button_panel = MultiComponentEnableDisablePanel(
            None,
            None,
            opts.get("Buttons", []),
            id=f"{opts.get('label', 'MultiSystem')}_subsystem_panel",
            classes="detector_subsystem",
        )

        button_tab = self._initalise_system(panel_name, opts, button_panel)

        map_panel = ScrollableContainer(
            Static(
                ComponentLevelTree(None, None, opts.get("Buttons", [])).print_tree(),
                id=f"tree_view_{opts.get('label', 'MultiSystem')}",
            ),
            id=f"{opts.get('label', 'MultiSystem')}_view_container",
        )
        map_tab = self._initalise_system(opts.get("view_panel", ""), opts, map_panel)

        return button_tab, map_tab
