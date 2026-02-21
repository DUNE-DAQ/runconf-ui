
from runconf_ui import state_operations
from runconf_ui.utils import get_class_from_segment_list

from ..config_dataclasses import DisableAttributeData
from .factory_interface import FactoryInterface


class AttributeOperationFactory(FactoryInterface):
    def create(self, attr_config: DisableAttributeData) -> list[state_operations.StateOperationContainerOr] | None:
        dal_list = get_class_from_segment_list(
            self.configuration,
            attr_config.segments,
            attr_config.class_name,
        )
        if not dal_list:
            return None

        operations = [
            state_operations.DisableAttribute(
                self.configuration,
                self.session,
                dal,
                attr_config.id,
                attr_config.enabled_state,
                attr_config.disabled_state,
            )
            for dal in dal_list if not self.is_dal_filtered(dal, attr_config.filters)
        ]

        return [state_operations.StateOperationContainerOr(
            self.configuration,
            self.session,
            state_operations=operations,
        )]
