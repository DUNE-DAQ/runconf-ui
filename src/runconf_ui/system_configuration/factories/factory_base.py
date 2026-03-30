from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.utils import class_in_config, dal_in_config

from ..dataclasses import FilterData

TData = TypeVar("TData")
TResult = TypeVar("TResult")


class FactoryBase(ABC, Generic[TData, TResult]):
    def __init__(self, configuration: Configuration, session: DalBase):
        self.configuration = configuration
        self.session = session

    @abstractmethod
    def create(self, data: TData) -> TResult: ...

    def resolve_dals(
        self,
        class_name: str,
        object_id: str | None = None,
    ) -> list[DalBase] | None:
        """Checks if a DAL(s) exists, if it does return the dal(s)"""
        if not class_in_config(self.configuration, class_name):
            return None
        if object_id:
            if not dal_in_config(self.configuration, class_name, object_id):
                return None
            return [self.configuration.get_dal(class_name, object_id)]
        return self.configuration.get_dals(class_name)

    @staticmethod
    def is_filtered(dal: DalBase, filters: list[FilterData]) -> bool:
        """Is a given DAL object filtered?"""
        for f in filters:
            if not hasattr(dal, f.attribute):
                return False
            if getattr(dal, f.attribute) in f.values:
                return True
        return False
