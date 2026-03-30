from pathlib import Path
from typing import cast

from textual import on
from textual.containers import Grid
from textual.types import NoSelection
from textual.widgets import Button, Select, Static

from runconf_ui.utils import get_logger

from ..messages import (
    DaqSessionSelectedMessage,
    DaqVersionSelectedMessage,
    LoadConfigMessage,
)


class VersionSelect(Select[str]):
    @on(Select.Changed)
    def handle_selection_changed(self, event: Select.Changed):
        """
        Handle selection change events and emit a DaqVersionSelectedMessage with the selected version.
        """

        selected_version = (
            cast(str, event.value) if not isinstance(event.value, NoSelection) else None
        )
        get_logger().debug("Selected version %s", selected_version)
        self.post_message(DaqVersionSelectedMessage(daq_version=selected_version))


class SessionSelect(Select[Path]):
    @on(Select.Changed)
    def handle_selection_changed(self, event: Select.Changed):
        """
        Handle selection change events and emit a DaqSessionSelectedMessage with the selected session.
        NoSelection is replaced with None to ensure consistency with the backend
        """
        selected_session = (
            cast(str, event.value) if not isinstance(event.value, NoSelection) else None
        )
        get_logger().debug("Selected session %s", selected_session)
        self.post_message(DaqSessionSelectedMessage(daq_session=selected_session))


class FileSelect(Static):
    """
    A panel for selecting files.
    """

    def compose(self):
        get_logger().debug("Composing File select grid")

        with Grid(id="file-select-grid"):
            yield VersionSelect(
                id="version-select",
                options=[],
                classes="file_select_drop",
                prompt="Select DAQ Version",
            )
            yield SessionSelect(
                id="session-select",
                options=[],
                disabled=True,
                classes="file_select_drop",
                prompt="Select DAQ Session",
            )
            yield Button(
                "Open", id="open_file_button", disabled=True, classes="file_io_button"
            )
            yield Static("No Config Loaded", id="config_info")

    def update_versions(self, versions: list[str]):
        """
        Update the list of DAQ versions available for selection.
        """
        get_logger().debug(f"Updating versions to {versions}")

        opts = [(str(v), v) for v in versions]

        version_select: VersionSelect = self.query_one(VersionSelect)
        version_select.set_options(opts)
        self.enable_session_select()

    def update_sessions(self, sessions: list[str] | list[Path]):
        """
        Update the list of DAQ sessions available for selection.
        """
        get_logger().debug(f"Updating sessions to {sessions}")

        opts: list[tuple[str, Path]] = [
            (s.name if isinstance(s, Path) else s, Path(s)) for s in sessions
        ]
        session_select: SessionSelect = self.query_one(SessionSelect)
        session_select.set_options(opts)

    def enable_session_select(self):
        """
        Enable or disable the session select dropdown.
        """
        get_logger().debug("Enabling session selection")
        version_select = self.query_one(VersionSelect)
        session_select = self.query_one(SessionSelect)
        session_select.disabled = not self._select_enabled(version_select)

    def enable_open_button(self):
        """Enable or disable the open button based on whether a session is selected."""
        get_logger().debug("Enabling open button")

        session_select = self.query_one(SessionSelect)
        open_button = self.query_one("#open_file_button", Button)
        open_button.disabled = not self._select_enabled(session_select)

    def update_text(self, update_text: str | None):
        text_query: Static = self.query_one("#config_info", Static)
        if not text_query:
            return

        if update_text is None:
            update_text = "No Config Loaded"

        get_logger().debug("Updating text to %s", update_text)

        text_query.update(update_text)

    @on(Button.Pressed, ".file_io_button")
    def handle_open_pressed(self, _: Button.Pressed):
        """
        Handle open button press events and emit a DaqSessionSelectedMessage with the selected session.
        """
        session_select: SessionSelect = self.query_one(SessionSelect)
        selected_session = session_select.value
        get_logger().debug("Open config button pressed")

        if selected_session is not None:
            self.post_message(LoadConfigMessage())

    def _select_enabled(self, select: Select) -> bool:
        v = select.value

        return (v is not None) and (not isinstance(v, NoSelection))
