from abc import ABC, abstractmethod
from collections.abc import Sequence

from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.state_operations import StateOperation
from runconf_ui.utils import class_in_config, dal_in_config

from ..config_dataclasses import FilterData, SystemElementData


class FactoryInterface(ABC):
    def __init__(self, configuration: Configuration, session: DalBase):
        self.configuration = configuration
        self.session = session

    @abstractmethod
    def create(self, object_conf: SystemElementData) -> Sequence[StateOperation]:
        ...

    def resolve_dals(
        self,
        object_class: str,
        object_id: str | None = None,
    ) -> list[DalBase] | None:
        if not class_in_config(self.configuration, object_class):
            return None

        if object_id:
            if not dal_in_config(self.configuration, object_class, object_id):
                return None
            return [self.configuration.get_dal(object_class, object_id)]

        return self.configuration.get_dals(object_class)

    @classmethod
    def is_dal_filtered(cls, dal: DalBase, filters: list[FilterData]) -> bool:
        for f in filters:
            attribute = f.attribute
            if not hasattr(dal, attribute):
                return False
            if getattr(dal, attribute) in f.values:
                return True
        return False