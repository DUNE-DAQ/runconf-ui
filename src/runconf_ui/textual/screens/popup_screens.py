from dataclasses import dataclass
from typing import Literal

from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, LoadingIndicator

from runconf_ui.utils import get_logger

from ..messages import (
    CancelQuitMessage,
    QuitAndSaveMessage,
    QuitAndScrapMessage,
    QuitMessage,
)

ButtonVariants = Literal["default", "primary", "success", "warning", "error"]


class LoadingScreen(ModalScreen):
    """Blocking modal shown while a config is being opened."""

    def __init__(self, message: str = "Loading configuration..."):
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        get_logger().debug("Loading")
        with Vertical(id="loading-box"):
            yield Label(self._message, id="loading-label")
            yield LoadingIndicator()


@dataclass(frozen=True)
class ButtonTemplate:
    button: Button
    message: QuitMessage

    @classmethod
    def make(
        cls,
        label: str,
        variant: ButtonVariants,
        button_id: str,
        message: QuitMessage,
        disabled: bool = False,
    ) -> "ButtonTemplate":
        get_logger().debug(
            f"Making button with label={label}, variant={variant}, id={button_id}, classes='pop_up_button', disabled={disabled}), {message}"
        )

        return cls(
            Button(
                label=label,
                variant=variant,
                id=button_id,
                classes="pop_up_button",
                disabled=disabled,
            ),
            message,
        )


class ButtonPopup(ModalScreen):
    """Pop-up screen with a label and a set of buttons, each mapped to a message."""

    def __init__(self, buttons: list[ButtonTemplate], info_str: str, css_classes: str):
        super().__init__(classes="pop_up_screen")
        self._buttons = {t.button.id: t for t in buttons}
        self._info_str = info_str
        self._css_classes = css_classes

    def compose(self):
        with Grid(id="pop_grid", classes=self._css_classes):
            yield Label(self._info_str, classes="quit_question")
            for template in self._buttons.values():
                yield template.button

    def on_mount(self):
        num_buttons = len(self._buttons)
        grid = self.query_one("#pop_grid")
        grid.styles.grid_size_columns = num_buttons
        self.query_one(".quit_question").styles.column_span = num_buttons

    @on(Button.Pressed)
    def handle_button_press(self, event: Button.Pressed):
        template = self._buttons.get(event.button.id)
        if template is not None:
            self.post_message(template.message)


class QuitScreen(ButtonPopup):
    def __init__(self, can_create: bool):
        get_logger().debug("initialising quit screen")
        super().__init__(
            buttons=[
                ButtonTemplate.make(
                    "Create Config and Quit",
                    "success",
                    "create_quit_button",
                    QuitAndSaveMessage(),
                    disabled=not can_create,
                ),
                ButtonTemplate.make(
                    "Quit Without Creating Config?",
                    "warning",
                    "quit_scrap_button",
                    QuitAndScrapMessage(),
                ),
                ButtonTemplate.make(
                    "Cancel and Continue Editing",
                    "error",
                    "cancel_button",
                    CancelQuitMessage(),
                ),
            ],
            info_str="Quit Runconf-UI?",
            css_classes="pop_up quit_pop_up_grid",
        )


class CreateScreen(ButtonPopup):
    def __init__(self):
        get_logger().debug("initialising create screen")
        super().__init__(
            buttons=[
                ButtonTemplate.make(
                    "Create Config and Quit",
                    "success",
                    "create_quit_button",
                    QuitAndSaveMessage(),
                ),
                ButtonTemplate.make(
                    "Cancel and Continue Editing",
                    "error",
                    "cancel_button",
                    CancelQuitMessage(),
                ),
            ],
            info_str="Quit Runconf-UI?",
            css_classes="pop_up quit_pop_up_grid",
        )
