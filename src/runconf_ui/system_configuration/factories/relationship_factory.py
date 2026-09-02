from copy import copy

from conffwk.dal import DalBase

from runconf_ui.state_tree import Group

from ..dataclasses import ExcludableRelationshipData
from .attribute_factory import (
    AttributeFactory,
)


class RelationshipFactory(AttributeFactory[ExcludableRelationshipData]):
    """Creates Group nodes for exclude relationships.

    Creates the same Group structure as AttributeFactory but first resolves
    enabled_state and excluded_state strings to DAL objects.
    """

    def create(self, data: ExcludableRelationshipData) -> Group | None:
        """Create relationship group from configuration data.

        :param data: ExcludableRelationshipData specifying the relationships
        :returns: Group containing Leaf nodes, or None if unable to resolve states
        :rtype: Group | None
        """
        data = copy(data)

        included = self._resolve_state(data.included_state, data.relationship_class)
        excluded = self._resolve_state(data.excluded_state, data.relationship_class)

        if included is None or excluded is None or included == excluded:
            return None

        data.included_state = included
        data.excluded_state = excluded

        return super().create(data)

    def _resolve_state(
        self,
        state_id: str | list[str],
        state_class: str,
    ) -> DalBase | list[DalBase] | None:
        """Resolve included/excluded state identifiers to DAL objects.

        :param state_id: State identifier (string, list of strings, or empty)
        :param state_class: The DAL class to resolve into
        :returns: Resolved DAL object(s), or None if resolution fails
        :rtype: DalBase | list[DalBase] | None
        """
        if not state_id:
            return []

        if isinstance(state_id, str):
            dals = self.resolve_dals(state_class, state_id)
            return dals[0] if dals else None

        if isinstance(state_id, list):
            resolved = [self.resolve_dals(state_class, d) for d in state_id]
            results = [d[0] for d in resolved if d is not None]

            return results if results else None

        return state_id
