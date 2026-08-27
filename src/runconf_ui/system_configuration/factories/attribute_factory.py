from typing import TypeVar

from runconf_ui.state_tree import (
    AttributeAdapter,
    Group,
    Leaf,
)
from runconf_ui.utils import get_class_from_segment_list

from ..dataclasses import ExcludableAttributeData
from .factory_base import FactoryBase

TIncludeableAttributeData = TypeVar("TIncludeableAttributeData", bound=ExcludableAttributeData)


class AttributeFactory(FactoryBase[TIncludeableAttributeData, "Group | None"]):
    """Creates a Group node containing Leaf nodes for disable attributes.

    Creates a Group node (strategy=any) containing one Leaf per matching DAL.
    OR semantics: the attribute group is considered included if any DAL has
    the attribute included.
    """

    def create(self, data: TIncludeableAttributeData) -> Group | None:
        """Create attribute group from configuration data.

        :param data: DisableAttributeData specifying the attributes to create
        :returns: Group containing Leaf nodes, or None if no matching DALs
        :rtype: Group | None
        """
        dal_list = get_class_from_segment_list(
            self.configuration,
            data.segments,
            data.class_name,
        )
        if not dal_list:
            return None

        group = Group(strategy=any)
        for dal in dal_list:
            if not self.is_filtered(dal, data.filters):
                group.add(
                    Leaf(
                        AttributeAdapter(
                            self.configuration,
                            self.session,
                            dal,
                            data.id,
                            data.included_state,
                            data.excluded_state,
                        ),
                        tooltip=getattr(dal, data.tooltip, dal.id)
                        if data.tooltip
                        else dal.id,
                    )
                )

        return group if group.children else None
