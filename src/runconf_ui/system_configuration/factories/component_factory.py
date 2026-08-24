from runconf_ui.state_tree import IncludeComponent, Leaf

from ..dataclasses import IncludeableElementData
from .factory_base import FactoryBase


class ComponentFactory(FactoryBase["IncludeableElementData", "list[Leaf] | None"]):
    """Creates Leaf nodes for disable components.

    Returns a list because one config entry can expand to many components
    when each_component_separate=True.
    """

    def create(self, data: IncludeableElementData) -> list[Leaf] | None:
        """Create component leaf nodes from configuration data.

        :param data: IncludeableElementData specifying the components to create
        :returns: List of Leaf nodes, or None if no matching DALs
        :rtype: list[Leaf] | None
        """
        dals = self.resolve_dals(data.class_name, data.id or None)
        if dals is None:
            return None

        return [
            Leaf(
                IncludeComponent(self.configuration, self.session, dal),
                label=dal.id if data.each_component_separate else "",
                tooltip=getattr(dal, data.tooltip, dal.id) if data.tooltip else dal.id,
            )
            for dal in dals
            if not self.is_filtered(dal, data.filters)
        ]
