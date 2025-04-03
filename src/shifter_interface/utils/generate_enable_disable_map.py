from runconf_ui.widgets.multicomponent_panel import MultiComponentEnableDisablePanel
from runconf_ui.widgets.single_component_panel import SingleComponentEnableDisablePanel
from runconf_ui.interfaces.controller.application_controller import ShifterInterfaceState

from textual.widgets import TabPane, Static
from textual.containers import ScrollableContainer


class EnableDisableMapGen:
    def __init__(self, app_controller: ShifterInterfaceState) -> None:
        self._app_controller = app_controller
        self._panel_list, self._map_list, self._panel_labels = self.read_panel_options()

    def read_panel_options(self):
        # Grab all panels we specify in the YAML
        panel_opts = self._app_controller.interface_config.panel_options

        # To be filled with panels
        panel_list = []

        # for multi system panels we also generate a map
        map_list = []
        panel_labels = [panel_opts[k]["label"] for k in panel_opts.keys()]

        for panel_name, opts in panel_opts.items():
            panel, map = self._parse_options(panel_name, opts)

            panel_list.append(panel)

            if map is not None:
                map_list.append(map)

        return panel_list, map_list, panel_labels

    def _parse_options(self, panel_name: str, opts: dict):
        panel_type = opts.get("panel_type", None)
        if panel_type == "singlesystem":
            return self.initialise_single_system(panel_name, opts), None

        elif panel_type == "multisystem":
            return self.initialise_multi_system(panel_name, opts)

        else:
            raise ValueError(f"Unknown panel type {opts.get('panel_type')}")

    def initialise_single_system(self, panel_name, opts):
        panel = SingleComponentEnableDisablePanel(
            self._app_controller,
            opts.get("classes", []),
            id=f"{opts.get('label', 'SingleSystem')}_subsystem_panel",
            classes="detector_subsystem",
        )

        return self._initalise_system(panel_name, opts, panel)

    def _initalise_system(self, panel_name, opts, panel):
        return TabPane(
            panel_name,
            panel,
            id=f"{opts.get('label', 'daq_system')}_tabs",
        )

    def initialise_multi_system(self, panel_name, opts):
        panel = MultiComponentEnableDisablePanel(
            self._app_controller,
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
