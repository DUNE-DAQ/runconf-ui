import os
import yaml

from runconf_ui.utils.path_or_env_check import path_or_env_check


# Class for reading a YAML config and producing panels
class ShifterConfigReader:
    def __init__(self, settings_config_file: str, **kwargs):
        with open(settings_config_file) as f:
            self._settings_config = yaml.safe_load(f)

        # We can get settings
        general_settings = self._settings_config.get("General", {})

        # Update with any user args
        general_settings.update(kwargs)

        self.daq_config_directory = general_settings.get(
            "daq_config_directory", f"{os.getcwd()}/configs"
        )
        # Generic settings
        self.default_config = general_settings.get("session_config", None)

        if self.default_config is None:
            raise ValueError("No default configuration file specified")

        self.session_name = general_settings.get("session_name", None)

        if self.session_name is None:
            raise ValueError("No session name specified")

        self.base_url = general_settings.get("base_url", None)

        self.operation_url = general_settings.get("operation_url", None)

        # Get settings from the detector config
        self._detector_config = {}
        self._classes_to_show = []
        self.detector_config_settings = {}

    def open_detector_config(self, detector_config_file: str):
        with open(detector_config_file) as f:
            self._detector_config = yaml.safe_load(f)
        detector_config_settings = self._detector_config.get("Settings", {})
        self._classes_to_show = detector_config_settings.get("classes_to_show", [])

    @property
    def detector_config(self):
        return self._detector_config

    @property
    def output_directory(self):
        return f"{self._daq_config_directory}/../shifter_configs/{self._session_name}"

    @property
    def default_config(self):
        return self._default_config

    @default_config.setter
    def default_config(self, value):
        self._default_config = path_or_env_check(value)

    @property
    def daq_config_directory(self):
        return self._daq_config_directory

    @daq_config_directory.setter
    def daq_config_directory(self, value):
        self._daq_config_directory = path_or_env_check(value)

    @property
    def session_name(self):
        return self._session_name

    @session_name.setter
    def session_name(self, value):
        self._session_name = path_or_env_check(value)

    @property
    def base_url(self):
        return self._base_url

    @base_url.setter
    def base_url(self, value):
        self._base_url = path_or_env_check(value)

    @property
    def operation_url(self):
        return self._operation_url

    @operation_url.setter
    def operation_url(self, value):
        self._operation_url = os.getenv(value)

    @property
    def panel_options(self):
        return self._detector_config.get("PanelOptions", {})

    @property
    def adjustable_attributes(self):
        """
        Get the adjustable attributes from the detector config.
        This is a dictionary of attributes that can be adjusted in the UI.
        """
        return self._detector_config.get("AdjustableAttributes", {})

    @property
    def classes_to_show(self):
        """
        Get the set of classes to show in the UI.
        This is a set of class names that should be displayed.
        """
        return list(set(self._classes_to_show))
