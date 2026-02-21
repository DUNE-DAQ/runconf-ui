"""
Interface layer for doing any operation on objects with in the configuration
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.exceptions import AttributeValueException, StateBindingError

T = TypeVar("T")


class StateOperation(ABC, Generic[T]):
    def __init__(self, configuration: Configuration, session: DalBase, label=""):
        self.configuration = configuration
        self.session = session
        self.label = label

    @abstractmethod
    def set_state(self, state_val: T): ...

    @abstractmethod
    def get_state(self) -> T: ...


class DisableOperation(StateOperation[bool]):
    """Pure interface class, disable operation for enable/disable"""
    def __init__(self, configuration: Configuration, session: DalBase, label=""):
        super().__init__(configuration, session, label)
        self._bound_state: None | DisableOperation = None
        self._containers = []

    def bind_state(self, new_state_source: 'DisableOperation'):
        '''
        I miss pointers... this ensures controlled objects will ALWAYS share the state of their parents
        '''
        if self._bound_state:
            raise StateBindingError("Error cannot bind state twice")
        
        self.set_state(new_state_source.get_state())
        self._bound_state = new_state_source
    
    # Okay now we get HAKCY
    def add_top_level_container(self, container):
        '''Add a containing object'''
        self._containers.append(container)

    def get_state(self) -> bool:
        '''
        Gets the full state of an object, this talks to parents
        '''
        if self._bound_state is not None:
            # Necessary to ensure we always use and have the value of the bound state
            self._set_state(self._bound_state.get_state())
            return self._bound_state.get_state()
        
        # If everything containing us is disabled, so are we
        if self._containers and not all(c.get_state() for c in self._containers):
            return False
        
        return self._get_state()

    def get_internal_state(self) -> bool:
        """Gets the internal state of this object, does not talk to parents"""
        if self._bound_state is not None:
            return self._bound_state.get_internal_state()
        return self._get_state()

    def set_state(self, state_val: bool):
        if self._bound_state is not None:
            raise StateBindingError(
                f"Cannot set state on '{self.label}' directly — it is bound to an external state source."
            )

        self.set_internal_state(state_val)
        

    def set_internal_state(self, state_val) -> None:
        """Sets the internal state of this object, does not talk to parents"""
        if not isinstance(state_val, bool):
            raise AttributeValueException("Tried to set toggleable DAL to non-bool value")
        
        self._set_state(state_val)


    @abstractmethod
    def _get_state(self) -> bool: ...

    @abstractmethod
    def _set_state(self, state_val: bool): ...
