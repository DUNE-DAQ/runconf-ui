from runconf_ui.state_tree import AdjustableAttribute, Leaf

from ..dataclasses import AdjustableAttributeData
from .factory_base import FactoryBase


class AdjustableFactory(FactoryBase["AdjustableAttributeData", "list[Leaf] | None"]):
    """Creates Leaf nodes for adjustable attributes.

    Creates Leaf(AdjustableAttribute) nodes for configuration attributes that
    can be adjusted/modified by the user (e.g., trigger rates, thresholds).
    """

    def create(self, data: AdjustableAttributeData) -> list[Leaf] | None:
        """Create adjustable attribute leaf nodes from configuration data.

        :param data: AdjustableAttributeData specifying the attributes to create
        :returns: List of Leaf nodes, or None if no matching DALs
        :rtype: list[Leaf] | None
        """
        dals = self.resolve_dals(data.class_name, data.id or None)
        if dals is None:
            return None

        results = [
            Leaf(
                AdjustableAttribute(
                    self.configuration,
                    self.session,
                    dal,
                    data.attribute_name,
                ),
                label=f"{dal.id} - {data.attribute_name}",
                tooltip=getattr(dal, data.tooltip, dal.id) if data.tooltip else dal.id,
            )
            for dal in dals
            if not self.is_filtered(dal, data.filters)
        ]
        return results or None
