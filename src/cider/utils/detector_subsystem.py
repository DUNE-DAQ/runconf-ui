from typing import Any, Optional, List, NamedTuple


class SubsystemInfo(NamedTuple):
    """Helper class to store subsystem information."""

    type: str  # attribute/relationship/component
    class_name: str  # name of affected class
    id: str  # Either name of attribute or class ID
    enabled_state: Any  # Value when enabled
    disabled_state: Any  # Value when disabled
    # For attributes
    affected_objects: Optional[List] = (
        None  # List of objects affected by attribute. If None then all objects are affected
    )
    relationship_name: str = ""  # Name of relationship if subsystem is a relationship
