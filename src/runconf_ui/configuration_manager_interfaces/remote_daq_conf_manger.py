# Make backwards compatible with runconftools
try:
    from runconftools.ConfPool import ConfPool
except ImportError:
    from config_management.ConfPool import ConfPool
except Exception:
    raise ImportError(
        "Could not import runconftool or config_management. Please install runconftools or config_management"
    )

from runconf_ui.daq_config_interfaces.daq_config_file_io.daq_conf_path_reader import DaqConfPathReader
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)
from runconf_ui.configuration_manager_interfaces.management_interface import ManagementInterface

import re
from pathlib import Path
import logging
import traceback
import shutil

from runconf_ui.exceptions import CiderInvalidRepoException

class RemoteDaqConfManager(ManagementInterface):
    def __init__(self, application_controller: ShifterInterfaceState):
        """
        Initialize the remote management interface
        """
        super().__init__(application_controller)

        if self.application_controller.apparatus is None:
            raise ValueError(
                "Apparatus not set! Please set the APPARATUS in your env or use the --apparatus flag"
            )
        try:
            self.conf_pool = ConfPool(
                str(self.application_controller.shifter_interface_config.download_directory),
                apparatus=self.application_controller.apparatus,
                operation_url=self.application_controller.shifter_interface_config.operation_url,
                base_url=self.application_controller.shifter_interface_config.base_url,
            )
        except Exception:
            logging.error(traceback.format_exc())
            self.reset()


    def get_daq_versions(self) -> list[str]:
        """
        Get the list of DAQ versions
        """
        return self.conf_pool.get_daq_versions()

    def get_configurations(self) -> list[str]:
        """
        Get the list of DAQ configurations
        """
        if self._daq_version == "":
            return []

        return self.conf_pool.get_confs(re.compile(f"^{self._daq_version}$"))

    def open_file(self, daq_configuration: str):
        try:
            self.conf_pool.checkout_conf(daq_configuration, self._daq_version)
        # Reset conf_pool if we get an error
        except Exception as e:
            logging.error(traceback.format_exc())
            CiderInvalidRepoException(e)

        # Now we can open the file
        config_path_reader = DaqConfPathReader()
        
        # Logic for single file
        if self.application_controller.direct_config_path.is_file():
            return super().open_file(self.application_controller.direct_config_path)
        
        config_list = config_path_reader(
            self.application_controller.shifter_interface_config.download_directory
        )
        
        valid_config_files = [c for c in config_list if c.name == self.application_controller.shifter_interface_config.default_config]

        if len(valid_config_files) == 0:
            logging.error(
                f"Could not find config file for {daq_configuration}. Found: {config_list}"
            )
            logging.error(traceback.format_exc())
            raise Exception(
                f"Could not find config file for {daq_configuration}. Found: {config_list}"
            )

        if len(valid_config_files) > 1:
            logging.warning(
                f"Found multiple config files with the same name: {valid_config_files}, using the first one"
            )

        config_file = valid_config_files[0] 
        
        return super().open_file(Path(config_file))

    def get_default_version(self) -> str:
        """
        Get the default DAQ version
        """
        return self.conf_pool.get_release()
    
    def reset(self):
        '''
        Occasionally the conf pool gets corrupted. This is a workaround to reset it.
        '''
        logging.info("Resetting conf pool")

        # self.make_writable_and_log(self.application_controller.shifter_interface_config.download_directory)
        if self.conf_pool.repo:
            self.conf_pool.repo.close()
        
        shutil.rmtree(self.application_controller.shifter_interface_config.download_directory)

        Path(self.application_controller.shifter_interface_config.download_directory).mkdir(
            parents=True, exist_ok=True
        )

        self.__init__(self.application_controller)