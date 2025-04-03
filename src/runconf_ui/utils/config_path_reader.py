import runconf_ui.interfaces.actions.actions as ca
from runconf_ui.interfaces.controller.config_wrapper import ConfigurationWrapper

from pathlib import Path
from typing import List
import os


class ConfigPathReader:
    def __init__(
        self, default_config: str | None = None, default_session_name: str | None = None
    ):
        """
        Initialize the ConfigPathReader with a configuration file.
        """
        self._default_config = default_config
        self._default_session = default_session_name

    def get_db_from_path(self, file_path: Path) -> Path | None:
        """Returns a database path if the file is a valid configuration.
        Slightly chunky, but it makes the the code easier to read.
        """
        if ".data.xml" not in str(file_path):
            return None

        if not file_path.is_file():
            return None

        if self._default_config is not None and self._default_config not in str(
            file_path
        ):
            return None

        if self._get_number_of_sessions(str(file_path)) < 0:
            return None

        return file_path

    def _get_number_of_sessions(self, config_file_path: str) -> int:
        """Returns the number of sessions in the given configuration file."""
        try:
            config_file = ConfigurationWrapper(config_file_path)

            if self._default_session is None:
                filter = lambda _: True
            else:
                filter = (
                    lambda s: ca.GetAttributeAction(config_file)(s, "id")
                    == self._default_session
                )

            return len(
                [
                    s
                    for s in ca.GetDalsOfClassAction(config_file)("Session")
                    if filter(s)
                ]
            )
        except Exception:
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
