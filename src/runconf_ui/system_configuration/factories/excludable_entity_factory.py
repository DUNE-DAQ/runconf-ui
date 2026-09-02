from runconf_ui.state_tree import ExcludableEntityAdapter, Leaf

from ..dataclasses import ExcludableElementData
from .factory_base import FactoryBase


class ExcludableEntityFactory(FactoryBase["ExcludableElementData", "list[Leaf] | None"]):
    """Creates Leaf nodes for ExcludableEntities.

    Returns a list because one config entry can expand to many ExcludableEntities
    when each_ExcludableEntity_separate=True.
    """

    def create(self, data: ExcludableElementData) -> list[Leaf] | None:
        """Create ExcludableEntity leaf nodes from configuration data.

        :param data: ExcludableElementData specifying the ExcludableEntities to create
        :returns: List of Leaf nodes, or None if no matching DALs
        :rtype: list[Leaf] | None
        """
        dals = self.resolve_dals(data.class_name, data.id or None)
        if dals is None:
            return None

        return [
            Leaf(
                ExcludableEntityAdapter(self.configuration, self.session, dal),
                label=dal.id if data.each_component_separate else "",
                tooltip=getattr(dal, data.tooltip, dal.id) if data.tooltip else dal.id,
            )
            for dal in dals
            if not self.is_filtered(dal, data.filters)
        ]
