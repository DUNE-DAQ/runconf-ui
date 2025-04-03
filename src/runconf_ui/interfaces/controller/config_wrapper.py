import conffwk

class ConfigurationWrapper(conffwk.Configuration):
    """
    Small wrapper layer around the configuration. In principal this allows configuration interface
    to be extended. Currently it just removes the need to add oksconflibs: to a file
    """

    def __init__(self, configuration_file_path: str):
        super().__init__(f"oksconflibs:{configuration_file_path}")

        self._file_name: str = configuration_file_path

    @property
    def file_name(self) -> str:
        return self._file_name
