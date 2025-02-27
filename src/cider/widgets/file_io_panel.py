import cider.interfaces.actions.actions as ca
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from textual.containers import Grid
from textual.visual import SupportsVisual
from textual.widgets import Button, Static, Select
from textual.message import Message
from textual.reactive import reactive
from typing import List, Optional, Tuple
import os
from pathlib import Path
import logging

from cider.utils.management_interface import ManagementInterface


class FileIOPanel(Static):
    """
    I/O panel for selecting a configuration file and session.
    """

    branch_options = reactive([])
    version_options = reactive([])
    file_options = reactive([])

    def __init__(
        self,
        default_config: str = "",
        install_path: str = "",
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

        self._default_config = default_config

        self._install_path = install_path
        # Make it if it doesn't exist
        Path(self._install_path).mkdir(parents=True, exist_ok=True)
        self._manager = ManagementInterface(self._install_path)

        self._branch_options = self._manager.get_base_branches()

        self._selected_branch = None
        self._selected_version_name = None
        self._selected_config_name = default_config
        self._selected_session_name = None

        self._configuration = None

        self._default_config = default_config

    def compose(self):
        with Grid(id="file_io_panel_grid"):
            # Base branch menu
            yield Select(
                [(b, b) for b in self._branch_options],
                prompt="Select a Base Branch",
                id="select_base_branch",
                classes="file_select",
            )
            yield Select(
                [(b, b) for b in self.version_options],
                prompt="Select a Version",
                id="select_version",
                classes="file_select",
                disabled=True,
            )

            yield Select(
                [],
                prompt="Select a Session",
                id="select_session",
                classes="file_select",
                disabled=True,
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

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handles changes to the select widgets."""
        if event.select.id == "select_base_branch":
            self._select_new_branch(event.value)
        elif event.select.id == "select_version":
            self._select_new_version(event.value)
        elif event.select.id == "select_session":
            self._selected_session_name = (
                event.value if event.value != Select.BLANK else ""
            )
            self._update_button_state()

    def _update_button_state(self) -> None:
        """Updates the state of the open button based on selected config and session."""
        self.query_one("#open_file_button").disabled = not self._selected_session_name

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handles the button press event."""
        if event.button.id == "open_file_button" and self._selected_session_name:
            self.query_one("#file_io_panel_message").update(
                f"   [bold green]Current Config[/bold green]: [deep_pink4]{self._configuration.file_name}[/deep_pink4]\n   [bold green]Session[/bold green]:  [deep_pink4]{self._selected_session_name}"
            )
        else:
            self._deconfigure()

    def _open_new_file(self, file_path) -> None:
        """Handles opening a new file and updating the session list."""
        self._selected_config_name = file_path

        self._configuration = ConfigurationWrapper(self._selected_config_name)

        # Grab all the sessions available
        session_list = [
            (
                ca.GetAttributeAction(self._configuration)(i, "id"),
                ca.GetAttributeAction(self._configuration)(i, "id"),
            )
            for i in ca.GetDalsOfClassAction(self._configuration)("Session")
        ]

        self._update_selection_list(session_list, "select_session")

    def _update_selection_list(
        self, options: List[Tuple[str, str]], list_id: str
    ) -> None:
        try:
            self.query_one(f"#{list_id}").set_options(options)
            logging.info(options)

            if len(options):
                self.query_one(f"#{list_id}").disabled = False
            else:
                self.query_one(f"#{list_id}").disabled = True

        except Exception as e:
            logging.warning(f"Failed to update {list_id} select: {e}")

    def _select_new_branch(self, branch_name):
        if branch_name == Select.BLANK:
            self._selected_branch = None
            self._update_selection_list([], "select_version")
            return self._reset_version_select()

        self._manager.release = branch_name
        self._selected_branch = branch_name
        self.version_options = [(m, m) for m in self._manager.get_confs()]
        self._update_selection_list(self.version_options, "select_version")

    def _select_new_version(self, version_name):
        if version_name == Select.BLANK:
            self._selected_version_name = None
            return self._reset_file_select()

        self._selected_version_name = version_name

        self._manager.checkout_conf(version_name)

        self.file_options = self._generate_selection_list(self._install_path)

        for f in self.file_options:
            if self._default_config in f:
                self._open_new_file(f)

    def _reset_version_select(self) -> None:
        self._selected_version_name = None
        self._reset_file_select()

    def _reset_file_select(self) -> None:
        self._selected_config_name = None
        self._selected_session_name = None
        self._update_selection_list([], "select_session")

    def _deconfigure(self) -> None:
        """Resets the panel to its default state."""
        self._selected_config_name = ""
        self._configuration = None
        self._selected_session_name = Select.BLANK
        self._update_selection_list([], "select_session")
        self.query_one("#file_io_panel_message").update(
            "[bold medium_violet_red]   No file loaded\n  "
        )
        self.post_message(self.Deconfigured())

    @property
    def selected_config_name(self) -> str | None:
        """Returns the selected configuration name."""
        return self._selected_config_name

    @property
    def selected_session_name(self) -> str | None:
        """Returns the selected session name."""
        return self._selected_session_name

    # FILE STUFF
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
                        database_list.append(str(db))

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

    class Deconfigured(Message):
        """Message sent when the panel is deconfigured."""

    class PathChanged(Message):
        """Message sent when the file list changes."""
