import cider.interfaces.actions.actions as ca
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.utils.file_system_watcher import FileSystemWatcher
from watchdog.observers import Observer
import threading
from textual.containers import Grid
from textual.visual import SupportsVisual
from textual.widgets import Button, Static, Select
from textual.message import Message
from textual.reactive import reactive
from typing import List, Optional, Tuple
import os
from pathlib import Path
import logging

# from config_management import ConfPool


class FileIOPanel(Static):
    """
    I/O panel for selecting a configuration file and session.
    """

    # Reactive to auto-update widgets
    file_options = reactive([])

    def __init__(
        self,
        search_directory: str | List[str],
        default_config: str,
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
        self._configuration: Optional[ConfigurationWrapper] = None
        self._selected_config_name: str = ""
        self._selected_session_name: str = ""

        # Defaults
        self._default_config = default_config

        self.file_options = self._generate_selection_list(self._search_directory)

        # Start the directory watcher in a separate thread
        self._observer = Observer()
        self._watcher = FileSystemWatcher(self)
        self._start_directory_watch()

    # ========================== Watch Methods ==========================
    def _start_directory_watch(self) -> None:
        """Starts watching for changes in the directory."""
        watch_dirs = (
            [Path(p) for p in self._search_directory.split(":")]
            if isinstance(self._search_directory, str)
            else [Path(p) for p in self._search_directory]
        )

        for directory in watch_dirs:
            if directory.is_dir():
                self._observer.schedule(self._watcher, str(directory), recursive=True)

        thread = threading.Thread(target=self._observer.start, daemon=True)
        thread.start()

    def refresh_file_list(self) -> None:
        """Refreshes the file selection list when files are modified."""
        new_options = self._generate_selection_list(self._search_directory)
        if new_options != self.file_options:  # Update only if changes occur
            self.file_options = new_options
            self._update_file_select()
            self.post_message(self.PathChanged())

    def watch_file_options(self) -> None:
        """Updates the file select widget when file_options changes."""
        try:
            self.query_one("#select_file").set_options(self.file_options)
            default = self._get_default_config_value()
            if default:
                self.query_one("#select_file").value = default[1]
        except Exception as e:
            logging.warning(f"Failed to update file select: {e}")

    def on_unmount(self) -> None:
        """Stops the observer when the panel is unmounted."""
        self._observer.stop()
        self._observer.join()

    # ========================== UI Methods ==========================

    def compose(self):
        """Composes the UI elements."""
        with Grid(id="file_io_panel_grid"):
            file_val = self._get_default_file_value()
            yield Select(
                self.file_options,
                prompt="Select a File",
                id="select_file",
                classes="file_select",
                value=file_val,
            )

            session_options = self._get_session_options(file_val)
            yield Select(
                [(s, s) for s in session_options],
                prompt="Select a Session",
                id="select_session",
                classes="file_select",
            )

            yield Button(
                "Open",
                id="open_file_button",
                disabled=True,
                classes="file_io_button",
            )

            yield Static(
                "[bold medium_violet_red]   No file loaded\n  ",
                id="file_io_panel_message",
            )

    def _get_default_file_value(self) -> str:
        """Returns the default file value if available, otherwise Select.BLANK."""
        default = self._get_default_config_value()
        return default[1] if default else Select.BLANK

    def _get_session_options(self, file_val: str) -> List[str]:
        """Returns the session value and options based on the selected file."""
        if file_val == Select.BLANK:
            return Select.BLANK, []

        self._open_new_file(file_val)
        session_list = [
            ca.GetAttributeAction(self._configuration)(i, "id")
            for i in ca.GetDalsOfClassAction(self._configuration)("Session")
        ]
        return session_list

    def _open_new_file(self, file_name: str) -> None:
        """Handles opening a new file and updating the session list."""
        if file_name == Select.BLANK:
            self._selected_config_name = None
            self._selected_session_name = None
            self._update_session_select([])
            return

        self._selected_config_name = file_name
        self._configuration = ConfigurationWrapper(self._selected_config_name)

        # Grab all the sessions available
        session_list = [
            (
                ca.GetAttributeAction(self._configuration)(i, "id"),
                ca.GetAttributeAction(self._configuration)(i, "id"),
            )
            for i in ca.GetDalsOfClassAction(self._configuration)("Session")
        ]

        self._update_session_select(session_list)

    def _update_session_select(self, options: List[Tuple[str, str]]) -> None:
        """Updates the session select widget with the given options."""
        try:
            self.query_one("#select_session").set_options(options)
        except Exception as e:
            logging.warning(f"Failed to update session select: {e}")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handles changes to the select widgets."""
        if event.select.id == "select_file":
            self._open_new_file(event.value)
        elif event.select.id == "select_session":
            self._selected_session_name = (
                event.value if event.value != Select.BLANK else ""
            )
            self._update_button_state()

    def _update_button_state(self) -> None:
        """Updates the state of the open button based on selected config and session."""
        self.query_one("#open_file_button").disabled = not (
            self._selected_config_name and self._selected_session_name
        )

    def on_button_pressed(self) -> None:
        """Handles the button press event."""
        if self._selected_config_name and self._selected_session_name:
            self.query_one("#file_io_panel_message").update(
                f"   [bold green]Current Config[/bold green]: [deep_pink4]{self._configuration.file_name}[/deep_pink4]\n   [bold green]Session[/bold green]:  [deep_pink4]{self._selected_session_name}"
            )
        else:
            self._deconfigure()

    def _deconfigure(self) -> None:
        """Resets the panel to its default state."""
        self._selected_config_name = ""
        self._configuration = None
        self._selected_session_name = Select.BLANK
        self._update_session_select([])
        self.query_one("#file_io_panel_message").update(
            "[bold medium_violet_red]   No file loaded\n  "
        )
        self.post_message(self.Deconfigured())

    def _get_default_config_value(self) -> Optional[Tuple[str, str]]:
        """Returns the default config value if available."""
        return next(
            (i for i in self.file_options if self._default_config == i[0]), None
        )

    @classmethod
    def _generate_selection_list(
        cls, session_directories: str | List[str]
    ) -> List[Tuple[str, str]]:
        """Generates a list of file options from the given directories."""
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
                db = cls._get_db_from_path(item)
                if db:
                    database_list.append((str(db.name), str(db)))

                if not item.is_dir():
                    continue

                for sub_item in item.iterdir():
                    db = cls._get_db_from_path(sub_item)
                    if db:
                        database_list.append((str(db.name), str(db)))

        return database_list

    @classmethod
    def _get_db_from_path(cls, file_path: Path) -> Optional[Path]:
        """Returns a database path if the file is a valid configuration."""
        if file_path.is_file() and ".data.xml" in str(file_path):
            if cls._get_number_of_sessions(str(file_path)) > 0:
                return file_path
        return None

    @classmethod
    def _get_number_of_sessions(cls, config_file_path: str) -> int:
        """Returns the number of sessions in the given configuration file."""
        try:
            config_file = ConfigurationWrapper(config_file_path)
            return len(ca.GetDalsOfClassAction(config_file)("Session"))
        except Exception:
            return 0

    @property
    def selected_config_name(self) -> str:
        """Returns the selected configuration name."""
        return self._selected_config_name

    @property
    def selected_session_name(self) -> str:
        """Returns the selected session name."""
        return self._selected_session_name

    # ========================== Messages ==========================
    class Deconfigured(Message):
        """Message sent when the panel is deconfigured."""

    class PathChanged(Message):
        """Message sent when the file list changes."""
