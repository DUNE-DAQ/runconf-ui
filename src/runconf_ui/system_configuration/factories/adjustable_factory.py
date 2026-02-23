from runconf_ui.state_tree import Leaf, AdjustableAttribute

from ..dataclasses import AdjustableAttributeData
from .factory_base import FactoryBase

class AdjustableFactory(FactoryBase):
    """
    Creates Leaf(AdjustableAttribute) nodes.

    These are added to the tree with votes=False, propagate=False by the
    builder — they are never touched by Group.set() and do not influence
    any parent's aggregated state.

    compute_state() will report PARENT_DISABLED for these nodes when either
    their parent group is off or their DAL is resource-disabled in the session,
    allowing the UI to grey out the corresponding text box appropriately.
    """

    def create(self, data: AdjustableAttributeData) -> list[Leaf] | None:
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
                label=dal.id,
            )
            for dal in dals
            if not self.is_filtered(dal, data.filters)
        ]
        return results or None


