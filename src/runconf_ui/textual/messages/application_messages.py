"""
Messages related to the application itself.
"""

from textual.message import Message


class ApplicationMessage(Message):
    """Base class for messages related to application state changes."""

    ...


class OpenQuitMenuMessage(ApplicationMessage):
    """Message emitted when the application should quit."""

    ...


class OpenCreateMenuMessage(ApplicationMessage):
    """Message emitted when the application should quit."""

    ...


class QuitMessage(ApplicationMessage):
    """Message emitted when the application should quit."""

    ...


class QuitAndSaveMessage(QuitMessage): ...


class QuitAndScrapMessage(QuitMessage): ...


class CancelQuitMessage(QuitMessage): ...


class LoadConfigMessage(ApplicationMessage):
    """Message emitted when a new configuration should be loaded."""

    ...


class OpenHelpMenuMessage(ApplicationMessage):
    """Message emitted when the user requests help."""

    ...


class SaveConfigMessage(ApplicationMessage):
    """Message emitted when the current configuration should be saved."""

    ...


class RefreshMessage(ApplicationMessage): ...
