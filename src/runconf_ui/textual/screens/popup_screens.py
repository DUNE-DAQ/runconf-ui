from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, LoadingIndicator


class LoadingScreen(ModalScreen):
    '''Blocking modal shown while a config is being opened.'''

    DEFAULT_CSS = """
    LoadingScreen {
        align: center middle;
        background: black 60%;
    }
    #loading-box {
        width: 40;
        height: 7;
        border: thick $primary-background-darken-3 80%;
        background: $primary-background;
        padding: 1 2;
        align: center middle;
        layout: vertical;
    }
    #loading-label {
        width: 100%;
        content-align: center middle;
        color: white;
    }
    """

    def __init__(self, message: str = "Loading configuration..."):
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        yield Label(self._message, id="loading-label")
        yield LoadingIndicator()