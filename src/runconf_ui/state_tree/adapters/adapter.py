from abc import ABC, abstractmethod
from typing import Any

from conffwk import Configuration
from conffwk.dal import DalBase

class Adapter(ABC):
    """
    Reads and writes state for a single DAL object.
    Has no knowledge of the tree it lives in.
    """

    def __init__(self, configuration: Configuration, session: DalBase, dal: DalBase):
        self.configuration = configuration
        self.session = session
        self.dal = dal

    @abstractmethod
    def get(self) -> Any: ...

    @abstractmethod
    def set(self, value: Any) -> None: ...


    def dal_enabled(self) -> bool:
        """
        Whether the underlying DAL is enabled as a resource in the session.

        This is a read-only check available on all adapters. For DisableResource
        this is the primary state. For DisableAttribute and AdjustableAttribute
        it is a secondary check — the DAL may be resource-disabled independently
        of the attribute value or the tree structure.
        """
        return self.dal not in self.session.disabled

