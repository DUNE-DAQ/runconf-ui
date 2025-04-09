import runconf_ui.interfaces.actions.actions as ca
from runconf_ui.interfaces.controller.daq_conf_wrapper import DaqConfigurationWrapper
from runconf_ui.utils.daq_conf_tools.consolidate_daq_conf import ConsolidateDAQConf

from pathlib import Path
from typing import List
import os
import logging

class DaqConfPathReader:
    def get_db_from_path(self, file_path: Path) -> Path | None:
        """Returns a database path if the file is a valid configuration.
        Slightly chunky, but it makes the the code easier to read.
        """
        if ".data.xml" not in str(file_path):
            return None

        if not file_path.is_file():
            return None

        if self._get_number_of_sessions(str(file_path)) < 1:
            return None

        return file_path


    def _get_number_of_sessions(self, config_file_path: str) -> int:
        """Returns the number of sessions in the given configuration file."""
        try:
            daq_config_file = DaqConfigurationWrapper(config_file_path)
                    
            return len([s for s in ca.GetDalsOfClassAction(daq_config_file)("Session")])
        except Exception as e:  
            logging.debug(f"Error reading configuration file {config_file_path}: {e}")
            return 0        
            

    # FILE STUFF
    def __call__(self, config_directories) -> List[Path]:
        """Generates a list of file options from the given directories."""

        self.config_directories = config_directories

        if isinstance(self.config_directories, str):
            self.config_directories = (
                [os.getcwd()]
                if not self.config_directories
                else [Path(p) for p in self.config_directories.split(":")]
            )
        else:
            self.config_directories = [self.config_directories]

        database_list = []
        for directory in self.config_directories:
            if not isinstance(directory, Path):
                continue
            
            
            if not directory.is_dir():
                continue

            for item in directory.iterdir():
                db = self.get_db_from_path(item)
                if db:
                    database_list.append(db)

                if not item.is_dir():
                    continue

                for sub_item in item.iterdir():
                    db = self.get_db_from_path(sub_item)
                    if db:
                        database_list.append(db)

        return database_list
