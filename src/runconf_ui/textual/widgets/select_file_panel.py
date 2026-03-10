from pathlib import Path

from textual import on
from textual.containers import Grid
from textual.types import NoSelection
from textual.widgets import Button, Select, Static

from ..messages import (
    DaqSessionSelectedMessage,
    DaqVersionSelectedMessage,
    LoadConfigMessage,
)


class VersionSelect(Select):
    @on(Select.Changed)
    def handle_selection_changed(self, event: Select.Changed):
        '''
        Handle selection change events and emit a DaqVersionSelectedMessage with the selected version.
        '''
        selected_version = event.value
        if isinstance(selected_version, NoSelection):
            selected_version = None
        
        self.post_message(DaqVersionSelectedMessage(daq_version=selected_version))
        
class SessionSelect(Select):
    @on(Select.Changed)
    def handle_selection_changed(self, event: Select.Changed):
        '''
        Handle selection change events and emit a DaqSessionSelectedMessage with the selected session.
        NoSelection is replaced with None to ensure consistency with the backend
        '''
        selected_session = event.value
        if isinstance(selected_session, NoSelection):
            selected_session = None

        self.post_message(DaqSessionSelectedMessage(daq_session=selected_session))


class FileSelect(Static):
    '''
    A panel for selecting files.
    '''
    def compose(self):
        with Grid(id="file-select-grid"):
            yield VersionSelect(id="version-select", options=[], classes="file_select_drop")
            yield SessionSelect(id="session-select", options=[], disabled=True, classes="file_select_drop")
            yield Button(
                "Open", id="open_file_button", disabled=True, classes="file_io_button"
            )
            yield Static("No Config Loaded", id="config_info")

    def update_versions(self, versions: list[str]):
        '''
        Update the list of DAQ versions available for selection.
        '''
        opts = [(str(v), v) for v in versions]
        
        version_select: VersionSelect= self.query_one(VersionSelect)
        version_select.set_options(opts)
        self.enable_session_select()
        
    def update_sessions(self, sessions: list[str | Path]):
        '''
        Update the list of DAQ sessions available for selection.
        '''
        opts = [(str(s.name),s) for s in sessions]
        
        session_select: SessionSelect = self.query_one(SessionSelect)
        session_select.set_options(opts)
    
    def enable_session_select(self):
        '''
        Enable or disable the session select dropdown.
        '''
        version_select: VersionSelect = self.query_one(VersionSelect)
        session_select: SessionSelect = self.query_one(SessionSelect)
        session_select.disabled = not self._select_enabled(version_select)
            
    def enable_open_button(self):
        '''Enable or disable the open button based on whether a session is selected.
        '''        
        session_select: SessionSelect = self.query_one(SessionSelect)
        open_button: Button = self.query_one("#open_file_button", Button)
        open_button.disabled = not self._select_enabled(session_select)
        
    def update_text(self, update_text: str|None):
        text_query = self.query("#config_info")
        if not text_query:
            return
        
        text = text_query.first()
        if update_text is None:
            update_text = "No Config Loaded"
        
        text.update(update_text)
        
    
    @on(Button.Pressed, ".file_io_button")
    def handle_open_pressed(self, _: Button.Pressed):
        '''
        Handle open button press events and emit a DaqSessionSelectedMessage with the selected session.
        '''
        session_select: SessionSelect = self.query_one(SessionSelect)
        selected_session = session_select.value
        if selected_session is not None:
            self.post_message(LoadConfigMessage())
            
    def _select_enabled(self, select: Select)->bool:
        v = select.value
        return (v is not None) and (not isinstance(v, NoSelection))