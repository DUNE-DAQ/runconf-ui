from runconf_ui.state_tree import Group

from conffwk.dal import DalBase

from .attribute_factory import (
    AttributeFactory,
)

from ..dataclasses import DisableRelationshipData

class RelationshipFactory(AttributeFactory):
    """
    Creates the same Group structure as AttributeFactory but first resolves
    enabled_state and disabled_state strings to DAL objects.
    """

    def create(self, data: DisableRelationshipData) -> Group | None:
        enabled = self._resolve_state(data.enabled_state, data.relationship_class)
        disabled = self._resolve_state(data.disabled_state, data.relationship_class)

        if enabled is None or disabled is None:
            return None

        data.enabled_state = enabled
        data.disabled_state = disabled
        return super().create(data)

    def _resolve_state(
        self,
        state_id: str | list[str],
        state_class: str,
    ) -> DalBase | list[DalBase] | None:
        if not state_id:
            return []

        if isinstance(state_id, str):
            dals = self.resolve_dals(state_class, state_id)
            return dals[0] if dals else None

        resolved = [
            self.resolve_dals(state_class, d)
            for d in state_id
        ]
        results = [d[0] for d in resolved if d is not None]
        return results if results else None
