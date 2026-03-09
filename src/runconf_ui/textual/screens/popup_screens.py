from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, LoadingIndicator
from textual.containers import Vertical

class LoadingScreen(ModalScreen):
    '''Blocking modal shown while a config is being opened.'''

    def __init__(self, message: str = "Loading configuration..."):
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="loading-box"):
            yield Label(self._message, id="loading-label")
            yield LoadingIndicator()
