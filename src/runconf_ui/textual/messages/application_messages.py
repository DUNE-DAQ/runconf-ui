"""
Messages related to the application itself.
"""

from textual.message import Message


class ApplicationMessage(Message):
    """Base class for messages related to application state changes."""

    ...


class OpenQuitMenuMessage(ApplicationMessage):
    """Message emitted when the application should open a quit confirmation menu.

    This message triggers the display of a menu asking the user to confirm
    whether they want to quit the application.
    """

    ...


class OpenCreateMenuMessage(ApplicationMessage):
    """Message emitted when the application should open a configuration creation menu.

    This message triggers the display of a menu for creating a new configuration.
    """

    ...


class QuitMessage(ApplicationMessage):
    """Message emitted when the application should quit."""

    ...


class QuitAndSaveMessage(QuitMessage):
    """Message emitted to save configuration changes before quitting the application."""

    ...


class QuitAndScrapMessage(QuitMessage):
    """Message emitted to discard configuration changes before quitting the application."""

    ...


class CancelQuitMessage(QuitMessage):
    """Message emitted to cancel the quit operation and return to the application."""

    ...


class LoadConfigMessage(ApplicationMessage):
    """Message emitted when a new configuration should be loaded.

    This message triggers configuration loading from the selected DAQ version
    and session.
    """

    ...


class OpenHelpMenuMessage(ApplicationMessage):
    """Message emitted when the user requests help.

    This message triggers the display of help documentation or usage information.
    """

    ...


class SaveConfigMessage(ApplicationMessage):
    """Message emitted when the current configuration should be saved.

    This message triggers the save operation for all pending configuration changes.
    """

    ...


class RefreshMessage(ApplicationMessage):
    """Message emitted to trigger a refresh of the application display.

    This message causes the UI to redraw and update all displayed information
    from the current state.
    """
