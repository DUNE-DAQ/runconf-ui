from conffwk.dal import DalBase

from runconf_ui import state_operations
from runconf_ui.system_configuration.factories.attribute_operation_factory import (
    AttributeOperationFactory,
)

from ..config_dataclasses import DisableRelationshipData


class RelationshipOperationFactory(AttributeOperationFactory):
    '''
    RelationshipOperationFactory is a special case of Attribut
    '''
    def create(self, rel_config: DisableRelationshipData) -> state_operations.StateOperationContainerOr | None:
        state_class = rel_config.relationship_class

        enabled = self._str_to_dal(rel_config.enabled_state, state_class)
        disabled = self._str_to_dal(rel_config.disabled_state, state_class)
        if enabled is None or disabled is None:
            return None

        rel_config.enabled_state = enabled
        rel_config.disabled_state = disabled
        return super().create(rel_config)


    def _str_to_dal(
        self, state_id: str | list[str], state_class: str
    ) -> DalBase | list[DalBase] | None:
        if not state_id:
            return []

        if isinstance(state_id, str):
            dals = self.resolve_dals(state_class, state_id)
            return dals[0] if dals else None

        results = [
            self.resolve_dals(state_class, d)
            for d in state_id
        ]
        resolved = [d[0] for d in results if d is not None]
        return resolved if resolved else None