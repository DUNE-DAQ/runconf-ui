"""
Textual Messages to communicate the state changes to the backend.
"""

from textual.message import Message


class StateChangeMessage(Message):
    """Base class for messages emitted when the configuration state changes.

    StateChangeMessage and its subclasses communicate state changes to the backend
    to trigger updates, persistence, or cascading configuration changes.
    """

    ...


class ConfigLoadedMessage(StateChangeMessage):
    """Emitted when a new configuration is successfully loaded and ready to display."""

    ...


class ConfigLoadFailedMessage(StateChangeMessage):
    """Emitted when a configuration load operation fails.

    This message indicates that the configuration could not be loaded, possibly
    due to file access issues, parsing errors, or missing dependencies.
    """

    ...


class NodeToggledMessage(StateChangeMessage):
    """Emitted when a DISABLE node is toggled on or off.

    This message triggers a state update in the backend and cascades to update
    any dependent nodes or attributes.
    """

    def __init__(self, group_id: str, widget_id: str):
        """Initialize NodeToggledMessage.

        :param group_id: The ID of the group containing the toggled node
        :param widget_id: The ID of the widget that was toggled
        """
        super().__init__()  # type: ignore
        self.group_id = group_id
        self.widget_id = widget_id


class ValueChangedMessage(StateChangeMessage):
    """Emitted when an ADJUSTABLE node's value is changed by the user.

    This message triggers a backend update to store the new value and propagate
    any configuration changes.
    """

    def __init__(self, group_id: str, widget_id: str, new_value):
        """Initialize ValueChangedMessage.
        :param group_id: The ID of the group containing the adjusted node
        :param widget_id: The ID of the widget with changed value
        :param new_value: The new value for the adjustable attribute
        """
        super().__init__()  # type: ignore
        self.group_id = group_id
        self.widget_id = widget_id
        self.new_value = new_value


class DaqVersionSelectedMessage(StateChangeMessage):
    """Emitted when a DAQ version is selected or deselected.

    This message triggers loading and display of available sessions and configurations
    for the newly selected DAQ version.
    """

    def __init__(self, daq_version: str | None):
        """Initialize DaqVersionSelectedMessage.

        :param daq_version: The selected DAQ version identifier, or None if deselected
        """
        self.daq_version = daq_version
        super().__init__()  # type: ignore


class DaqSessionSelectedMessage(StateChangeMessage):
    """Emitted when a DAQ session is selected or deselected.

    This message triggers loading and display of available configurations
    and the initial state tree for the selected session.
    """

    def __init__(self, daq_session: str | None):
        """Initialize DaqSessionSelectedMessage.

        :param daq_session: The selected DAQ session identifier, or None if deselected
        """
        self.daq_session = daq_session
        super().__init__()  # type: ignore
