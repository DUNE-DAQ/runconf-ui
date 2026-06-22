from abc import ABC, abstractmethod
from typing import Any

from conffwk import Configuration
from conffwk.dal import DalBase
from confmodel_dal import component_disabled


class Adapter(ABC):
    """Abstract base class for adapters that read and write DAL object state.

    Provides a uniform interface for accessing and modifying configuration state
    of individual DAL (Data Access Layer) objects without knowledge of the
    tree structure they exist within.
    """

    def __init__(self, configuration: Configuration, session: DalBase, dal: DalBase):
        """Initialize Adapter with configuration context.

        :param configuration: The configuration object containing DAL definitions
        :param session: The DAL session object providing context
        :param dal: The specific DAL object to adapt for state access
        """
        self.configuration = configuration
        self.session = session
        self.dal = dal

    @abstractmethod
    def get(self) -> Any:
        """Get the current state value for this DAL object.

        :returns: The current state value
        :rtype: Any
        """
        ...

    @abstractmethod
    def set(self, value: Any) -> None:
        """Set the state value for this DAL object.

        :param value: The new state value to set
        """
        ...

    def dal_enabled(self) -> bool:
        """Check if the underlying DAL is enabled as a resource in the session.

        This is a read-only check available on all adapters. For DisableComponent
        this is the primary state. For DisableAttribute and AdjustableAttribute,
        it is a secondary check — the DAL may be resource-disabled independently
        of the attribute value or the tree structure.

        :returns: True if the DAL is enabled, False if disabled
        :rtype: bool
        """
        return not component_disabled(
            self.configuration._obj, self.session.id, self.dal.id
        )
