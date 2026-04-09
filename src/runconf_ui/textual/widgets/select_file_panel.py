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
    """Select widget for choosing a DAQ version.

    Emits DaqVersionSelectedMessage when the selection changes.
    """

    @on(Select.Changed)
    def handle_selection_changed(self, event: Select.Changed):
        """Handle DAQ version selection changes.

        When the version selection changes, emits a DaqVersionSelectedMessage
        with the selected version identifier.

        :param event: The Select.Changed event
        """
        selected_version = (
            cast(str, event.value) if not isinstance(event.value, NoSelection) else None
        )
        get_logger().debug("Selected version %s", selected_version)
        self.post_message(DaqVersionSelectedMessage(daq_version=selected_version))


class SessionSelect(Select[Path | str]):
    @on(Select.Changed)
    def handle_selection_changed(self, event: Select.Changed):
        """Handle DAQ session selection changes.

        When the session selection changes, emits a DaqSessionSelectedMessage
        with the selected session identifier. NoSelection values are converted
        to None for consistency with the backend.

        :param event: The Select.Changed event
        """
        selected_session = (
            cast(str, event.value) if not isinstance(event.value, NoSelection) else None
        )
        get_logger().debug("Selected session %s", selected_session)
        self.post_message(DaqSessionSelectedMessage(daq_session=selected_session))


class FileSelect(Static):
    """Static widget panel for selecting DAQ version, session, and configuration file.

    Provides dropdown selectors for version and session, along with an open button
    and status text display.
    """

    def compose(self):
        """Compose the file selection grid with version, session, and button controls.

        :returns: A generator yielding child widgets
        """
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

    def set_default_version(self, default: str):
        version_select: VersionSelect = self.query_one(VersionSelect)

        opts = [o[1] for o in version_select._options]

        if default in opts:
            version_select.value = default
            self.enable_session_select()

    def update_versions(self, versions: list[str]):
        """Update the list of available DAQ versions in the selector.

        Populates the version dropdown with available versions and enables
        the session selector.

        :param versions: List of available DAQ version identifiers
        """
        get_logger().debug(f"Updating versions to {versions}")

        opts = [(str(v), v) for v in versions]

        version_select: VersionSelect = self.query_one(VersionSelect)
        version_select.set_options(opts)

        if len(opts) == 1:
            version_select.value = opts[0][1]
            self.enable_session_select()

    def update_sessions(self, sessions: list[str] | list[Path]):
        """Update the list of available DAQ sessions in the selector.

        Populates the session dropdown with available sessions for the current version.
        Accepts sessions as strings or Path objects.

        :param sessions: List of available DAQ session identifiers or paths
        """
        get_logger().debug(f"Updating sessions to {sessions}")

        opts: list[tuple[str, Path | str]] = [
            (s.name if isinstance(s, Path) else s, s) for s in sessions
        ]
        session_select: SessionSelect = self.query_one(SessionSelect)
        session_select.set_options(opts)  # type: ignore

        if len(opts) == 1:
            session_select.value = opts[0][1]

    def enable_session_select(self):
        """Enable or disable the session selector based on version selection.

        The session selector is enabled only when a version is selected.
        """
        get_logger().debug("Enabling session selection")
        version_select = self.query_one(VersionSelect)
        session_select = self.query_one(SessionSelect)
        session_select.disabled = not self._select_enabled(version_select)

    def enable_open_button(self):
        """Enable or disable the open button based on session selection.

        The open button is enabled only when a session is selected.
        """
        get_logger().debug("Enabling open button")

        session_select = self.query_one(SessionSelect)
        open_button = self.query_one("#open_file_button", Button)
        open_button.disabled = not self._select_enabled(session_select)

        # No selection + Only one opt
        if len(session_select._options) == 2:
            self.handle_open_pressed()

    def update_text(self, update_text: str | None):
        """Update the status text display.

        :param update_text: The text to display, or None to show "No Config Loaded"
        """
        text_query: Static = self.query_one("#config_info", Static)
        if not text_query:
            return

        if update_text is None:
            update_text = "No Config Loaded"

        get_logger().debug("Updating text to %s", update_text)

        text_query.update(update_text)

    @on(Button.Pressed, ".file_io_button")
    def handle_open_pressed(self):
        """Handle open button press events.

        When the open button is pressed, emits a LoadConfigMessage to trigger
        loading of the selected configuration.

        :param _: The Button.Pressed event (unused)
        """
        session_select: SessionSelect = self.query_one(SessionSelect)
        selected_session = session_select.value
        get_logger().debug("Open config button pressed")

        if selected_session is not None:
            self.post_message(LoadConfigMessage())

    def _select_enabled(self, select: Select) -> bool:
        """Check if a select control has a value selected.

        :param select: The Select widget to check
        :returns: True if a valid option is selected, False otherwise
        :rtype: bool
        """
        v = select.value

        return (v is not None) and (not isinstance(v, NoSelection))
