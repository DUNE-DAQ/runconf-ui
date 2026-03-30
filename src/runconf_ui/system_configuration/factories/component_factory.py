from runconf_ui.state_tree import DisableComponent, Leaf

from ..dataclasses import DisableElementData
from .factory_base import FactoryBase


class ComponentFactory(FactoryBase["DisableElementData", "list[Leaf] | None"]):
    """
    Creates Leaf nodes from DisableElementData (component entries in YAML).
    Returns a list because one config entry can expand to many components
    when each_component_separate=True.
    """

    def create(self, data: DisableElementData) -> list[Leaf] | None:
        dals = self.resolve_dals(data.class_name, data.id or None)
        if dals is None:
            return None

        return [
            Leaf(
                DisableComponent(self.configuration, self.session, dal),
                label=dal.id if data.each_component_separate else "",
                tooltip=getattr(dal, data.tooltip, dal.id) if data.tooltip else dal.id,
            )
            for dal in dals
            if not self.is_filtered(dal, data.filters)
        ]
