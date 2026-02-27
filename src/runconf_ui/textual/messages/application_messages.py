'''
Messages related to the application itself.
'''

from textual.message import Message

class ApplicationMessage(Message):
    """Base class for messages related to application state changes."""
    ...

class QuitMessage(ApplicationMessage):
    """Message emitted when the application should quit."""
    ...

class ResetMessage(ApplicationMessage):
    """Message emitted when the application should reset its data."""
    ...

class LoadConfigMessage(ApplicationMessage):
    """Message emitted when a new configuration should be loaded."""
    def __init__(self, config_path: str):
        super().__init__()
        self.config_path = config_path

class HelpMessage(ApplicationMessage):
    """Message emitted when the user requests help."""
    ...

class SaveConfigMessage(ApplicationMessage):
    """Message emitted when the current configuration should be saved."""
    ...
    