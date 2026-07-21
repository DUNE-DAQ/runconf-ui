from dataclasses import dataclass
from typing import Literal

from rich.markup import escape
from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, LoadingIndicator, Static

from runconf_ui.utils import get_logger

from ..messages import (
    CancelQuitMessage,
    QuitAndSaveMessage,
    QuitAndScrapMessage,
    QuitMessage,
)

ButtonVariants = Literal["default", "primary", "success", "warning", "error"]


class LoadingScreen(ModalScreen):
    """Modal loading screen shown during configuration loading.

    Displays a loading indicator and message while a configuration file
    is being loaded and processed.
    """

    def __init__(self, message: str = "Loading configuration..."):
        """Initialize LoadingScreen with a message.

        :param message: The message to display while loading
        """
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        """Compose the loading screen with message and indicator.

        :returns: A generator yielding loading screen widgets
        """
        get_logger().debug("Loading")
        with Vertical(id="loading-box"):
            yield Label(self._message, id="loading-label")
            yield LoadingIndicator()


@dataclass(frozen=True)
class ButtonTemplate:
    """Template for creating a button bound to a specific message.

    Encapsulates a Button widget and the message it should emit when pressed.
    """

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
        """Create a ButtonTemplate with the given properties.

        :param label: The button label text
        :param variant: The button styling variant
        :param button_id: The widget ID for the button
        :param message: The message to emit when button is pressed
        :param disabled: Whether the button should be initially disabled
        :returns: A new ButtonTemplate instance
        :rtype: ButtonTemplate
        """
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
    """Modal pop-up screen with configurable buttons and associated messages.

    Displays a label/prompt and a set of buttons, each mapped to emit a
    specific message when pressed. Used as a base for confirmation dialogs
    and other button-driven pop-ups.
    """

    def __init__(self, buttons: list[ButtonTemplate], info_str: str, css_classes: str):
        """Initialize ButtonPopup with button templates and information.

        :param buttons: List of ButtonTemplate objects defining buttons and their messages
        :param info_str: The information/prompt text to display
        :param css_classes: CSS classes to apply to the pop-up
        """
        super().__init__(classes="pop_up_screen")
        self._buttons = {t.button.id: t for t in buttons}
        self._info_str = info_str
        self._css_classes = css_classes

    def compose(self):
        """Compose the pop-up with label and buttons.

        :returns: A generator yielding pop-up widgets
        """
        with Grid(id="pop_grid", classes=self._css_classes):
            yield Static(f"[bold]{self._info_str}[/bold]", classes="quit_question")
            for template in self._buttons.values():
                yield template.button

    def on_mount(self):
        """Configure grid layout based on button count.

        Sets up the grid to span as many columns as there are buttons.
        """
        num_buttons = len(self._buttons)
        grid = self.query_one("#pop_grid")
        grid.styles.grid_size_columns = num_buttons
        self.query_one(".quit_question").styles.column_span = num_buttons

    @on(Button.Pressed)
    def handle_button_press(self, event: Button.Pressed):
        """Handle button press events and emit the associated message.

        :param event: The Button.Pressed event
        """
        template = self._buttons.get(event.button.id)
        if template is not None:
            self.post_message(template.message)


class QuitScreen(ButtonPopup):
    """Modal pop-up for quit confirmation with save/discard options.

    Presents options to quit and save configuration, quit without saving,
    or cancel and continue editing.
    """

    def __init__(self, can_create: bool):
        """Initialize QuitScreen.

        :param can_create: Whether configuration can be created (enables create-quit button)
        """
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
    """Modal pop-up for configuration creation.

    Presents options to create configuration and quit or cancel and continue editing.
    """

    def __init__(self):
        """Initialize CreateScreen."""
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


class ExceptionScreen(ButtonPopup):
    """Modal pop-up for displaying error messages.

    Presents an error message with an OK button to dismiss the error.
    """

    def __init__(self, error_msg: str):
        """Initialize ExceptionScreen.

        :param error_msg: The error message to display
        """
        get_logger().debug("initialising exception screen")
        super().__init__(
            buttons=[
                ButtonTemplate.make(
                    "OK",
                    "error",
                    "ok_button",
                    CancelQuitMessage(),
                ),
                ButtonTemplate.make(
                    "Quit Runconf-UI",
                    "warning",
                    "quit_scrap_button",
                    QuitAndScrapMessage(),
                ),
            ],
            info_str="Error handling config. This is likely due to incompatible config or older DAQ dependencies.\n"
                    f"The following error has been raised: \n [bold red]{escape(error_msg)}[/bold red]",
            css_classes="pop_up quit_pop_up_grid",
        )
