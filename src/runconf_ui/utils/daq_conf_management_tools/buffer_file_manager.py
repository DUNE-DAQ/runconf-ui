from runconf_ui.interfaces.controller.daq_conf_wrapper import DaqConfigurationWrapper
from runconf_ui.utils.daq_conf_tools.consolidate_daq_conf import ConsolidateDAQConf
from runconf_ui.interfaces.controller.application_controller import (
    ShifterInterfaceState,
)
from pathlib import Path
import os
import logging


class BufferFileManager:
    def __init__(self, application_controller: ShifterInterfaceState):
        '''
        Class to generate a temporary configuration file 
        '''
        self._application_controller = application_controller
        self.buffer_id = os.environ.get("SESSION_NAME", os.getlogin())
        self.TMP_CONFIG = Path(f"/tmp/shifter_configs-{self.buffer_id}/tmp_config.data.xml")

    def load_configuration(self):
        """Handle loading and consolidating the DAQ configuration"""
        self.TMP_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        
        logging.info(f"Session name {self._application_controller.session_name}")
        ConsolidateDAQConf(
            self._application_controller.current_daq_config,
            self._application_controller.session_name,
            "Session",
            str(self.TMP_CONFIG),
        )()
        
        self._application_controller.buffer_daq_config = DaqConfigurationWrapper(
            str(self.TMP_CONFIG)
        )
