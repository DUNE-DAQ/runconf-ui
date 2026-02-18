'''
Interface layer for doing any operation on objects with in the configuration
'''

from abc import ABC, abstractmethod
from conffwk.dal import DalBase
from conffwk import Configuration

from typing import Generic, TypeVar

T=TypeVar('T')
class StateOperation(ABC, Generic[T]):
    def __init__(self, configuration: Configuration, session: DalBase):
        self.configuration = configuration
        self.session = session
        
    @abstractmethod
    def set_state(self, state_val: T):
        ...
            
    @abstractmethod
    def get_state(self)->T:
        ...
        
class DisableOperation(StateOperation[bool]):
    '''Pure interface class, disable operation for enable/disable'''
    ...