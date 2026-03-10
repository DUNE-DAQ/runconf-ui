from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, LoadingIndicator, Button
from textual.containers import Vertical, Grid
from textual import on
from dataclasses import dataclass
from ..messages import (QuitMessage, 
                        QuitAndSaveMessage,
                        QuitAndScrapMessage,
                        CancelQuitMessage)

class LoadingScreen(ModalScreen):
    '''Blocking modal shown while a config is being opened.'''

    def __init__(self, message: str = "Loading configuration..."):
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="loading-box"):
            yield Label(self._message, id="loading-label")
            yield LoadingIndicator()

@dataclass(frozen=True)
class ButtonTemplate:
    button: Button
    message: QuitMessage
    
    @classmethod
    def make(cls, label: str, variant: str, button_id: str, message: QuitMessage) -> 'ButtonTemplate':
        return cls(Button(label=label, variant=variant, id=button_id), message)


class ButtonPopup(ModalScreen):
    '''Pop-up screen with a label and a set of buttons, each mapped to a message.'''

    def __init__(self, buttons: list[ButtonTemplate], info_str: str, css_classes: str):
        super().__init__()
        self._buttons = {t.button.id: t for t in buttons}
        self._info_str = info_str
        self._css_classes = css_classes

    def compose(self):
        with Grid(id="pop_grid", classes=self._css_classes):
            yield Label(self._info_str, classes="popup_info")
            for template in self._buttons.values():
                yield template.button

    @on(Button.Pressed)
    def handle_button_press(self, event: Button.Pressed):
        template = self._buttons.get(event.button.id)
        if template is not None:
            self.post_message(template.message)

class QuitScreen(ButtonPopup):
    def __init__(self):
        super().__init__(
            buttons=[
                ButtonTemplate.make("Create Config and Quit",       "success", "create_quit_button", QuitAndSaveMessage()),
                ButtonTemplate.make("Quit Without Creating Config?", "warning", "quit_scrap_button",  QuitAndScrapMessage()),
                ButtonTemplate.make("Cancel and Continue Editing",   "error",   "cancel_button",      CancelQuitMessage()),
            ],
            info_str="Quit Runconf-UI?",
            css_classes="quit_grid",
        )

class CreateScreen(ButtonPopup):
    def __init__(self):
        super().__init__(
            buttons=[
                ButtonTemplate.make("Create Config and Quit",       "success", "create_quit_button", QuitAndSaveMessage()),
                ButtonTemplate.make("Cancel and Continue Editing",   "error",   "cancel_button",      CancelQuitMessage()),
            ],
            info_str="Quit Runconf-UI?",
            css_classes="quit_grid",
        )