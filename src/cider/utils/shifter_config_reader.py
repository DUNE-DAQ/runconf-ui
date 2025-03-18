from cider.widgets.single_component_panel import SingleComponentEnableDisablePanel
from cider.widgets.multicomponent_panel import MultiComponentEnableDisablePanel

from textual.widgets import TabPane, Static
from textual.containers import ScrollableContainer
from cider.utils.path_or_env_check import path_or_env_check

import logging
import yaml
import os

"""
- Name:
    top_level_segment: seg
    

"""


# Class for reading a YAML config and producing panels
class ShifterConfigReader:
    def __init__(self, config_file, **kwargs):

        with open(config_file, "r") as f:
            self._config = yaml.safe_load(f)

        # We can get settings
        general_settings = self._config.get("General", {})

        # Update with any user args
        general_settings.update(kwargs)

        self._download_directory = path_or_env_check(general_settings.get("download_directory", f"{os.getcwd()}/configs"))
        # Generic settings
        self._default_config = path_or_env_check(general_settings.get("default_config", None))
        if self._default_config is None:
            raise ValueError("No default configuration file specified")
        
        self._session_name = path_or_env_check(general_settings.get("session_name", None))
        if self._session_name is None:
            raise ValueError("No session name specified")
        
        self._base_url = path_or_env_check(general_settings.get("base_url", None))
        if self._base_url is None:
            raise ValueError("No base url specified")
        
        self._operation_url = path_or_env_check(general_settings.get("operation_url", None))
        if self._operation_url is None:
            raise ValueError("No operation url specified")

        # Default config file
        self._panel_list, self._map_list, self._panel_labels = self.read_panel_options()

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
    def panel_list(self):
        return self._panel_list

    @property
    def map_list(self):
        return self._map_list

    @property
    def panel_labels(self):
        return self._panel_labels

    def read_panel_options(self):
        # Grab all panels we specify in the YAML
        panel_opts = self._config.get("PanelOptions", {})

        # To be filled with panels
        panel_list = []

        # for multi system panels we also generate a map
        map_list = []
        panel_labels = [panel_opts[k]["label"] for k in panel_opts.keys()]

        for panel_name, opts in panel_opts.items():
            panel, map = self._parse_options(panel_name, opts)

            panel_list.append(panel)

            if map is not None:
                map_list.append(map)

        return panel_list, map_list, panel_labels

    def _parse_options(self, panel_name: str, opts: dict):
        panel_type = opts.get("panel_type", None)
        if panel_type == "singlesystem":
            return self.initialise_single_system(panel_name, opts), None

        elif panel_type == "multisystem":
            return self.initialise_multi_system(panel_name, opts)

        else:
            raise ValueError(f"Unknown panel type {opts.get('panel_type')}")

    def initialise_single_system(self, panel_name, opts):
        panel = SingleComponentEnableDisablePanel(
            None,
            None,
            opts.get("classes", []),
            id=f"{opts.get('label', 'SingleSystem')}_subsystem_panel",
            classes="detector_subsystem",
        )

        return self._initalise_system(panel_name, opts, panel)

    def _initalise_system(self, panel_name, opts, panel):
        return TabPane(
            panel_name,
            panel,
            id=f"{opts.get('label', 'daq_system')}_tabs",
        )

    def initialise_multi_system(self, panel_name, opts):

        logging.debug(f"{panel_name} :: {opts}")

        panel = MultiComponentEnableDisablePanel(
            None,
            None,
            opts,
            id=f"{opts.get('label', 'MultiSystem')}_subsystem_panel",
            classes="detector_subsystem",
        )

        panel_tab = self._initalise_system(panel_name, opts, panel)

        map = ScrollableContainer(
            Static(
                panel.get_tree().print_tree(),
                id=f"tree_view_{opts.get('label', 'MultiSystem')}",
            ),
            id=f"{opts.get('label', 'MultiSystem')}_view_container",
        )

        map_tab = self._initalise_system(opts.get("view_panel", ""), opts, map)

        return panel_tab, map_tab
