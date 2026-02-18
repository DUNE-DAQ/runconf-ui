from dataclasses import dataclass

from conffwk import Configuration

"""
Dataclasses containing state information for the entire application
"""


@dataclass
class Environment:
    """
    Basic information about the environment. These are FIXED settings that will not change
    """

    apparatus: str
    save_file_name: str
    config_directory: str


@dataclass
class LocalEnvironment(Environment):
    """Local environment, currently a dummy class, kept for future development!"""
    ...

@dataclass
class RemoteEnvironment(Environment):
    operation_url: str
    base_url: str
    session_name: str

@dataclass
class AppState:
    """
    Current state of the application. These are non-fixed settings that will change
    """

    current_config_file: str
    current_selected_session: str
    buffer_file: Configuration
    environment: Environment
