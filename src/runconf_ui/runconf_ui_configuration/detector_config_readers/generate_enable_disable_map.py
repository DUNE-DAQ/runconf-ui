from runconf_ui.widgets.multicomponent_panel import MultiComponentEnableDisablePanel
from runconf_ui.runconf_ui_configuration.detector_config_readers.detector_map_reader_base import (
    DetectorMapReaderBase,
)
from textual.widgets import TabPane, Static
from textual.containers import ScrollableContainer

class EnableDisableMapGen(DetectorMapReaderBase):
    _panel_list = []
    _map_list = []
    
    def get_opts_from_controller(self) -> dict:
        """
        Get the options for the panels from the application controller.
        This method retrieves the panel options defined in the configuration.
        """
        return self._application_controller.shifter_interface_config.panel_options

    def append_to_panel(self, name, opts):
        panel, map = self.initialise_multi_system(name, opts)
        if panel is not None:
            self._panel_list.append(panel)
        if map is not None:
            self._map_list.append(map)
            

    def initialise_multi_system(self, panel_name, opts):
        panel = MultiComponentEnableDisablePanel(
            self._application_controller,
            opts,
            id=f"{opts.get('label', 'MultiSystem')}_subsystem_panel",
            classes="detector_subsystem",
        )

        panel_tab = self.initialise_system(panel_name, opts, panel)

        map = ScrollableContainer(
            Static(
                panel.get_tree().print_tree(),
                id=f"tree_view_{opts.get('label', 'MultiSystem')}",
            ),
            id=f"{opts.get('label', 'MultiSystem')}_view_container",
        )

        map_tab = self.initialise_system(opts.get("view_panel", ""), opts, map)

        return panel_tab, map_tab


    @property
    def map_list(self):
        return self._map_list

