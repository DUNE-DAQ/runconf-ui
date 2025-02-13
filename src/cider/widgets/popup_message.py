from textual.widgets import Static


class PopupMessage(Static):
    """A custom widget for displaying pop-up messages."""

    def on_mount(self):
        # Automatically remove the pop-up after 3 seconds
        self.set_timer(5.0, self.remove_popup)

    def remove_popup(self):
        """Remove the pop-up from the DOM."""
        self.remove()