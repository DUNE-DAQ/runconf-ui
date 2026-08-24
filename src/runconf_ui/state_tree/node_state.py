'''
State enum
'''
from enum import Enum, auto


class NodeState(Enum):
    """The state of a node."""
    ENABLED = (auto(), "#39b039")
    DISABLED = (auto(), "#808080")
    PARTIALLY_ENABLED=(auto(), "#d78700")
    PARENT_DISABLED = (auto(), "#808080")
    ERROR_STATE = (auto(), "#d70000")

    def __str__(self) -> str:
        return self.name
    
    def __repr__(self)->str:
        return self.name.lower().replace("_", " ")

    @property
    def idx(self):
        return self.value[0]
    
    @property
    def colour(self):
        return self.value[1]

    @staticmethod
    def bool_to_state(state_bool: bool)->"NodeState":
        if isinstance(state_bool, NodeState):
            return state_bool
        
        if state_bool:
            return NodeState.ENABLED
        else:
            return NodeState.DISABLED
        
    @staticmethod
    def state_to_bool(state: "NodeState")->bool:
        if isinstance(state, bool):
            return state
        return state in {NodeState.ENABLED, NodeState.PARTIALLY_ENABLED}
