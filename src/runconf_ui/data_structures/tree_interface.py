# Basic interface for all tree-like objects in the configuration
from abc import ABC, abstractmethod
from typing import List


from conffwk import Configuration
from conffwk.dal import DalBase
from confmodel_dal import component_disabled


from typing import Generic, TypeVar, Dict, List

T = TypeVar('T')
class TreeInterface(ABC, Generic[T]):
    '''
    We're gonna generate a tree object
    '''    
    def __init__(self, configuration: Configuration, session_name: str):
        self.configuration = configuration

        self.session_name = session_name
        self.session = self.configuration.get_dal("Session", session_name)

        # Caches
        self._is_disabled_cache = {}
    
    
        self._tree: Dict[T, List[T]] = self._build_tree()
        # Rather than inverting the full tree we'll just cache the parents if they're needed
        self._parent_cache: Dict[T, List[T]] = {}
        
    @abstractmethod
    def _build_tree(self)->Dict[T, List[T]]:
        ...
        
    @abstractmethod
    def find_node(self, key: T):
        return self._tree[key]
    
    @abstractmethod
    def _find_parents(self, key: T)->List[T]:
        parents = []
        for v, t in self._tree.items():
            if key in t:
                parents.append(v)
        return parents

    def find_parent(self, key: T):
        if key not in self._parent_cache:
            self._parent_cache[key] = self._find_parents(key)
        
        return self._parent_cache[key]
    
    @abstractmethod
    def is_disabled(self, obj: DalBase):
        ...