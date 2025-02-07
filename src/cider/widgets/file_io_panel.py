import cider.interfaces.actions.actions as ca
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper

from textual.containers import Grid
from textual.visual import SupportsVisual
from textual.widgets import Button, Static, Select

from typing import List
import os

class FileIOPanel(Static):
    
    def __init__(self, search_directory, content: str | SupportsVisual = "", *, expand: bool = False, shrink: bool = False, markup: bool = True, name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False) -> None:
        super().__init__(content, expand=expand, shrink=shrink, markup=markup, name=name, id=id, classes=classes, disabled=disabled)

        self._search_directory = search_directory
    
    def compose(self):
        
        file_options = self.generate_selection_list(self._search_directory)
        
        yield Grid(
            Select(file_options, prompt="Select a File", id="select_file", classes="file_select"),
            Select([], prompt="Select a Session", id="select_session", classes="file_select"),
            Button("Refresh", id="refresh_button"),
            id="file_io_panel_grid"
        )

    @classmethod
    def generate_selection_list(cls, session_directories: str | List[str] = ""):
        # Firstly find all databases
        database_list = []
        if isinstance(session_directories, str):
            if not session_directories:
                session_directories = [os.getcwd()]
            else:
                session_directories = [session_directories]

        for directory in session_directories:
            database_list += [
                f"{i}"
                for i in os.listdir(directory)
                if i.endswith(".data.xml")
            ]

        # For the simplified DB editor view we only want to show configurations containing sessions
        # while we're here we might as well cache the number of sessions
        database_list = [
            (file, cls.get_number_of_sessions(file))
            for file in database_list
            if cls.get_number_of_sessions(file)
        ]

        return database_list

    @classmethod
    def get_number_of_sessions(cls, config_file_path: str) -> int:
        # For now let's just search for "Session"... this is hacky but oh well
        # Open as config file
        try:
            config_file = ConfigurationWrapper(config_file_path)
            n_sessions = len(ca.GetDalsOfClassAction(config_file)("Session"))
        except:
            n_sessions = 0
        # Get total nimber of sesions in the config
        return n_sessions
    
    