
from runconf_ui.state_tree import (
    DisableAttribute,
    Group,
    Leaf,
)
from runconf_ui.utils import get_class_from_segment_list

from ..dataclasses import DisableAttributeData
from .factory_base import FactoryBase


class AttributeFactory(FactoryBase):
    """
    Creates a Group node (strategy=any) containing one Leaf per matching DAL.
    OR semantics: the attribute group is considered enabled if any DAL has
    the attribute enabled.
    """

    def create(self, data: DisableAttributeData) -> Group | None:
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
                        DisableAttribute(
                            self.configuration,
                            self.session,
                            dal,
                            data.id,
                            data.enabled_state,
                            data.disabled_state,
                        ),
                        label=dal.id,
                    )
                )

        return group if group.children else None
