from runconf_ui.utils.path_or_env_check import path_or_env_check

import yaml
import os


# Class for reading a YAML config and producing panels
class ShifterConfigReader:
    def __init__(self, config_file, **kwargs):

        with open(config_file, "r") as f:
            self._config = yaml.safe_load(f)

        # We can get settings
        general_settings = self._config.get("General", {})

        # Update with any user args
        general_settings.update(kwargs)

        self._download_directory = path_or_env_check(
            general_settings.get("download_directory", f"{os.getcwd()}/configs")
        )
        # Generic settings
        self._default_config = path_or_env_check(
            general_settings.get("default_config", None)
        )
        if self._default_config is None:
            raise ValueError("No default configuration file specified")

        self._session_name = path_or_env_check(
            general_settings.get("session_name", None)
        )
        if self._session_name is None:
            raise ValueError("No session name specified")

        self._base_url = path_or_env_check(general_settings.get("base_url", None))

        self._operation_url = path_or_env_check(
            general_settings.get("operation_url", None)
        )

        self._default_version = path_or_env_check(
            general_settings.get("default_daq_version", None)
        )

        self._default_daq_config = path_or_env_check(
            general_settings.get("default_daq_config", None)
        )

    @property
    def output_directory(self):
        return f"{self._download_directory}/../shifter_configs/{self._session_name}"

    @property
    def default_config(self):
        return self._default_config

    @default_config.setter
    def default_config(self, value):
        self._default_config = path_or_env_check(value)

    @property
    def download_directory(self):
        return self._download_directory

    @download_directory.setter
    def download_directory(self, value):
        self._download_directory = path_or_env_check(value)

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
        self._operation_url = path_or_env_check(value)

    @property
    def panel_options(self):
        return self._config.get("PanelOptions", {})

    @property
    def default_version(self):
        return self._default_version

    @property
    def default_daq_config(self):
        return self._default_daq_config
