from textual.screen import Screen
from textual.css.query import NoMatches

from runconf_ui.widgets.popup_message import PopupMessage


class PopupManager:
    def __init__(self, screen: Screen):
        self.screen = screen

    def show(self, message: str, timer: float = 10.0, success: bool = False):
        """Show a popup message"""
        self.remove()
        classes = "popup popup_success" if success else "popup popup_failure"
        popup = PopupMessage(message, timer, classes=classes)
        self.screen.query_one("#main_container").mount(popup)

    def remove(self):
        """Remove any existing popup"""
        try:
            existing_popup = self.screen.query_one(".popup", expect_type=PopupMessage)
            existing_popup.remove()
        except NoMatches:
            pass
