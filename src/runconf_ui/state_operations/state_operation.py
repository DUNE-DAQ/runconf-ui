"""
Interface layer for doing any operation on objects with in the configuration
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from conffwk import Configuration
from conffwk.dal import DalBase

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

    ...
