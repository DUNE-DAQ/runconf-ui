from runconf_ui.daq_config_interfaces.daq_config_file_io.consolidate_daq_conf import (
    ConsolidateDAQConf,
)
from runconf_ui.daq_config_interfaces.daq_config_file_io.daq_config_wrapper import (
    DaqConfigurationWrapper,
)
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)
from pathlib import Path
import os
import logging


class BufferFileManager:
    def __init__(self, application_controller: ShifterInterfaceState):
        """
        Class to generate a temporary configuration file
        """
        self._application_controller = application_controller
        self.buffer_id = os.environ.get("SESSION_NAME", os.getlogin())
        self.TMP_CONFIG = Path(
            f"/tmp/shifter_configs-{self.buffer_id}/tmp_config.data.xml"
        )

    def load_configuration(self):
        """Handle loading and consolidating the DAQ configuration"""
        self.TMP_CONFIG.parent.mkdir(parents=True, exist_ok=True)

        logging.debug(f"Session name {self._application_controller.session_name}")
        ConsolidateDAQConf(
            self._application_controller.current_daq_config,
            self._application_controller.session_name,
            "Session",
            str(self.TMP_CONFIG),
        )()

        self._application_controller.buffer_daq_config = DaqConfigurationWrapper(
            str(self.TMP_CONFIG)
        )
