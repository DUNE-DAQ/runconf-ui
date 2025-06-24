"""
Reads in a configuration file and generates a map of adjustable attributes.
"""

from runconf_ui.runconf_ui_configuration.detector_config_readers.detector_map_reader_base import (
    DetectorMapReaderBase,
)
from runconf_ui.widgets.adjustable_attribute_panel import AdjustableAttributePanel


class AdjustableAttributeMapGen(DetectorMapReaderBase):
    """
    Generates a map of adjustable attributes from the configuration.
    This class reads the configuration and creates panels for each adjustable attribute.
    """

    def get_opts_from_controller(self) -> dict:
        """
        Get the options for the panels from the application controller.
        This method retrieves the panel options defined in the configuration.
        """
        return (
            self._application_controller.shifter_interface_config.adjustable_attributes
        )

    def append_to_panel(self, name, opts):
        """
        Append a panel to the main container.
        This method creates a panel for the adjustable attribute and adds it to the panel list.
        """
        panels = self.initialise_adjustable_rate(name, opts)
        if panels:
            self._panel_list.append(panels)

    def initialise_adjustable_rate(self, panel_name, opts):
        panel = AdjustableAttributePanel(
            self._application_controller,
            opts,
            classes="detector_subsystem",
            id=f"{opts.get('label', 'AdjustableAttribute')}_subsystem_panel",
        )

        return self.initialise_system(panel_name, opts, panel)
