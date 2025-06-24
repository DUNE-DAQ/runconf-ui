import conffwk
import logging

# import oks


class DaqConfigurationWrapper(conffwk.Configuration):
    """
    Small wrapper layer around the configuration. In principal this allows configuration interface
    to be extended. Currently it just removes the need to add oksconflibs: to a file
    """

    def __init__(self, configuration_file_path: str):
        try:
            super().__init__(f"oksconflibs:{configuration_file_path}")

        except Exception:
            logging.error(
                f"Failed to open configuration file: {configuration_file_path}"
            )
            self.oks_dump(configuration_file_path)

        self.oks_dump()
        self._file_name: str = configuration_file_path

        logging.debug(f"Opening Configuration file: {configuration_file_path}")

    @property
    def file_name(self) -> str:
        return self._file_name
