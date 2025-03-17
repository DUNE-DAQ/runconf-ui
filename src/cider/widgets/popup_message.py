from textual.visual import SupportsVisual
from textual.widgets import Static


class PopupMessage(Static):
    """A custom widget for displaying pop-up messages."""
    def __init__(self, content: str | SupportsVisual = "", timer: float=10.0, *, expand: bool = False, shrink: bool = False, markup: bool = True, name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False) -> None:
        super().__init__(content, expand=expand, shrink=shrink, markup=markup, name=name, id=id, classes=classes, disabled=disabled)
        self._timer = timer
    
    def on_mount(self):
        # Automatically remove the pop-up after 3 seconds
        self.set_timer(self._timer, self.remove_popup)

    def remove_popup(self):
        """Remove the pop-up from the DOM."""
        self.remove()
