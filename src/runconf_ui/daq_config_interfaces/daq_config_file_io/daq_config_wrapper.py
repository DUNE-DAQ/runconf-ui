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

    # def oks_dump(self) -> None: ...

    @classmethod
    def oks_dump(cls, configuration_file_path: str)-> None:
        """
        Dump the contents of the configuration file.
        """
        logging.error(f"Dumping configuration file: {configuration_file_path}")
        oks_kernel = oks.OksKernel()
        oks_kernel.set_test_duplicated_objects_via_inheritance_mode(True)
        oks_kernel.load_file(str(configuration_file_path))

        for i in oks_kernel.schema_files():
            logging.info(f"Schema file: {i}")

        for i in oks_kernel.data_files():
            logging.info(f"Data file: {i}")
