'''
Textual Messages to communicate the state changes to the backend.
'''
from textual.message import Message


class StateChangeMessage(Message):
    """Message emitted when the state changes, prompting UI updates."""
    ...

class ConfigLoadedMessage(StateChangeMessage):
    """Emitted when a new configuration is loaded."""
    ...

class ConfigLoadFailedMessage(StateChangeMessage):
    """Emitted when loading a configuration fails."""
    ...

class NodeToggledMessage(StateChangeMessage):
    """Emitted when a DISABLE node is toggled."""
    def __init__(self, group_id: str, widget_id: str):
        super().__init__()
        self.group_id = group_id   
        self.widget_id = widget_id

class ValueChangedMessage(StateChangeMessage):
    """Emitted when an ADJUSTABLE node's value is changed."""
    def __init__(self, widget_id: str, new_value):
        super().__init__()
        self.widget_id = widget_id
        self.new_value = new_value
        
class DaqVersionSelectedMessage(StateChangeMessage):
    """Emitted when a DAQ version is selected."""
    def __init__(self, daq_version: str | None):
        super().__init__()
        self.daq_version = daq_version

class DaqSessionSelectedMessage(StateChangeMessage):
    """Emitted when a DAQ session is selected."""
    def __init__(self, daq_session: str | None):
        super().__init__()
        self.daq_session = daq_session