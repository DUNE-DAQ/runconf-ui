import cider.interfaces.actions.actions as ca
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.utils.shifter_config_reader import ShifterConfigReader
from cider.utils.management_interface import ManagementInterface
from typing import List, Optional, Tuple
import os
from pathlib import Path

class SelectionManager:
    '''
    For managing the selection of files and configurations
    
    '''
    def __init__(self, interface_config: ShifterConfigReader):
        self._manager = ManagementInterface(interface_config)
        self._default_config = interface_config.default_config
        self._install_path = interface_config.download_directory
        Path(self._install_path).mkdir(parents=True, exist_ok=True)

    def get_branch_options(self):
        return self._manager.get_config_version()

    def get_configuration_options(self, branch_name):
        self._manager.release = branch_name
        return [(m, m) for m in self._manager.get_confs()]

    def checkout_configuration(self, version_name):
        self._manager.checkout_conf(version_name)

    def get_file_options(self):
        return self._generate_selection_list(self._install_path)

    @staticmethod
    def _generate_selection_list(session_directories: str | List[str]) -> List[Tuple[str, str]]:
        if isinstance(session_directories, str):
            session_directories = (
                [os.getcwd()]
                if not session_directories
                else [Path(p) for p in session_directories.split(":")]
            )
        else:
            session_directories = [Path(p) for p in session_directories]

        database_list = []
        for directory in session_directories:
            if not directory.is_dir():
                continue

            for item in directory.iterdir():
                db = ConfigurationManager._get_db_from_path(item)
                if db:
                    database_list.append((str(db.name), str(db)))

                if not item.is_dir():
                    continue

                for sub_item in item.iterdir():
                    db = ConfigurationManager._get_db_from_path(sub_item)
                    if db:
                        database_list.append(str(db))

        return database_list

    @staticmethod
    def _get_db_from_path(file_path: Path) -> Optional[Path]:
        if file_path.is_file() and ".data.xml" in str(file_path):
            if ConfigurationManager._get_number_of_sessions(str(file_path)) > 0:
                return file_path
        return None

    @staticmethod
    def _get_number_of_sessions(config_file_path: str) -> int:
        try:
            config_file = ConfigurationWrapper(config_file_path)
            return len(ca.GetDalsOfClassAction(config_file)("Session"))
        except Exception:
            return 0