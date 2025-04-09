from datetime import datetime
import shutil
from runconf_ui.utils.file_cleaner import clean_old_files
import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)

from pathlib import Path
import logging

class SaveFileHandler:
    def __init__(self, application_controller: ShifterInterfaceState):
        """
        :param application_controller: The application controller
        """
        self._application_controller = application_controller
    
    def save_to_path(self, dir_path, name):
        logging.info(f"Saving configuration to {dir_path}/{name}")

        dir_path = Path(dir_path)

        # Clear itz
        if dir_path.is_dir():
            shutil.rmtree(dir_path)

        dir_path.mkdir(parents=True, exist_ok=True)

        output_file_path = f"{dir_path}/{name}"

        logging.debug(f"Copying configuration to {output_file_path}")
        ca.CopyFullConfigurationAction(
            self._application_controller.buffer_daq_config
        )(output_file_path)

        logging.info(f"Configuration saved to {output_file_path}")
        return output_file_path

    # Wrappers
    def save_main(self):
        self._application_controller.saved_configuration = self.save_to_path(
            f"{self._application_controller.shifter_interface_config.output_directory}/current_config",
            self.generate_output_name(),
        )
        self.generate_change_log(self._application_controller.saved_configuration)

    def save_backup(self):
        old_config_dir = Path(f"{self._application_controller.shifter_interface_config.output_directory}/old_configs")
        # make sure old config directory exists
        old_config_dir.mkdir(parents=True, exist_ok=True)

        clean_old_files(
            old_config_dir,
            extension=".data.xml",
            n_files=5,
            include_folders=True,
            folder_prefix="run_",
        )
        backup = self.save_to_path(
            f"{self._application_controller.shifter_interface_config.output_directory}/old_configs/run_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}",
            self.generate_output_name(),
        )
        
        self.generate_change_log(backup)

    def generate_output_name(self):
        # Hacky method to talk to the main screen
        full_path = self._application_controller.current_daq_config

        config_name = str(Path(full_path).name)
        config_name = config_name.replace(".data.xml", "")
        session = self._application_controller.session_name

        output_name = f"{config_name}_{session}"
        

        return f"{output_name}.data.xml"

    def generate_change_log(self, config_path):
        """
        Makes a log containing a summary of what was changed in the configuration
        """
        # HACK: This is a hack to save backup 
        # Not the cleanest but it works
        log_name = config_path.replace(".data.xml", "_changes.txt")
        
        if self._application_controller.saved_configuration is None:
            logging.info("No configuration saved, not creating change log")
            return
        
        logging.debug(f"Creating change log {log_name}")

        with open(f"{log_name}", "w") as file:
            # Loop over all enabled/disabled panels and get states
            for system, state in self._application_controller.current_state.items():
                file.write(f"\n{system}\n")
                file.write(f"{'-' * len(system)}\n")
                for key, value in state.items():
                    file.write(f"{key} : {value.name}\n")
            
    def __call__(self):
        logging.debug("Saving configuration")
        self.save_main()
        self.save_backup()
