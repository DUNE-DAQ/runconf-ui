from typing import Any, Optional, List, NamedTuple


class SubsystemInfo(NamedTuple):
    """Helper class to store subsystem information."""

    type: str
    class_name: str
    id: str
    enabled_state: Any
    disabled_state: Any
    affected_objects: Optional[List] = None
