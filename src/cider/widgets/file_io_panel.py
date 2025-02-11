import cider.interfaces.actions.actions as ca
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper

from textual.containers import Grid
from textual.visual import SupportsVisual
from textual.widgets import Button, Static, Select
from textual.message import Message

from typing import List
import os


class FileIOPanel(Static):

    def __init__(
        self,
        search_directory,
        content: str | SupportsVisual = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            content,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

        self._search_directory = search_directory
        self._configuration = None
        self._selected_config_name = ""
        self._selected_session_name = ""

    def compose(self):

        file_options = self.generate_selection_list(self._search_directory)

        yield Grid(
            Select(
                file_options,
                prompt="Select a File",
                id="select_file",
                classes="file_select",
            ),
            Select(
                [],
                prompt="Select a Session",
                id="select_session",
                classes="file_select",
            ),
            Button("Open", id="open_file_button", disabled=True, classes="file_io_button"),
            id="file_io_panel_grid",
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
                (i, f"{directory}/{i}")
                for i in os.listdir(directory)
                if i.endswith(".data.xml")
                and cls.get_number_of_sessions(f"{directory}/{i}")
            ]

        # For the simplified DB editor view we only want to show configurations containing sessions
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

    def on_select_changed(self, event: Select.Changed):

        if event.select.id == "select_file":
            if event.value == Select.BLANK:
                self._selected_config_name = ""
                self._configuration = None
                self._selected_session_name = Select.BLANK
                self.query_one("#select_session").set_options([])
                self.post_message(self.Deconfigured())
                return

            self._selected_config_name: str = event.value
            self._configuration = ConfigurationWrapper(self._selected_config_name)
            session_list = [
                (
                    ca.GetAttributeAction(self._configuration)(i, "id"),
                    ca.GetAttributeAction(self._configuration)(i, "id"),
                )
                for i in ca.GetDalsOfClassAction(self._configuration)("Session")
            ]

            self.query_one("#select_session").set_options(session_list)

        elif event.select.id == "select_session":

            if event.value == Select.BLANK:
                self._selected_session_name = ""
            else:
                self._selected_session_name: str = event.value

        if self._selected_config_name and self._selected_session_name:
            self.query_one("#open_file_button").disabled = False
        else:
            self.query_one("#open_file_button").disabled = True

    @property
    def configuration(self) -> ConfigurationWrapper | None:
        return self._configuration

    @property
    def selected_config_name(self) -> str:
        return self._selected_config_name

    @property
    def selected_session_name(self) -> str:
        return self._selected_session_name
    
    class Deconfigured(Message):
        def __init__(self):
            super().__init__()
    
    