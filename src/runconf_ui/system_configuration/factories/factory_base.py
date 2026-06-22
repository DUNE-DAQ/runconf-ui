from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.utils import class_in_config, dal_in_config

from ..dataclasses import FilterData

TData = TypeVar("TData")
TResult = TypeVar("TResult")


class FactoryBase(ABC, Generic[TData, TResult]):
    """Abstract base class for system component factories.

    Factories transform configuration dataclass definitions into state tree nodes.
    """

    def __init__(self, configuration: Configuration, session: DalBase):
        """Initialize the factory.

        :param configuration: The conffwk Configuration object
        :param session: The session DAL object
        """
        self.configuration = configuration
        self.session = session

    @abstractmethod
    def create(self, data: TData) -> TResult:
        """Create a node from the given data.

        :param data: The configuration data to transform
        :returns: The created node or appropriate result type
        """

    def resolve_dals(
        self,
        class_name: str,
        object_id: str | None = None,
    ) -> list[DalBase] | None:
        """Resolve DAL objects by class name and optional object ID.

        :param class_name: The DAL class name to resolve
        :param object_id: Optional specific DAL object ID to resolve
        :returns: List of resolved DAL objects, or None if not found
        :rtype: list[DalBase] | None
        """
        if not class_in_config(self.configuration, class_name):
            return None
        if object_id:
            if not dal_in_config(self.configuration, class_name, object_id):
                return None
            return [self.configuration.get_dal(class_name, object_id)]
        return self.configuration.get_dals(class_name)

    @staticmethod
    def is_filtered(dal: DalBase, filters: list[FilterData]) -> bool:
        """Check if a DAL object matches any of the given filters.

        :param dal: The DAL object to check
        :param filters: List of filter criteria
        :returns: True if the DAL matches a filter, False otherwise
        :rtype: bool
        """
        for f in filters:
            if not hasattr(dal, f.attribute):
                return False
            if getattr(dal, f.attribute) in f.values:
                return True
        return False
