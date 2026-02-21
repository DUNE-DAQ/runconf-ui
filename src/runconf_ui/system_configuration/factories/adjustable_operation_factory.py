from runconf_ui import state_operations

from ..config_dataclasses import AdjustableAttributeData
from .factory_interface import FactoryInterface


class AdjustableOperationFactory(FactoryInterface):
    def create(self, comp: AdjustableAttributeData) -> list[state_operations.AdjustableAttribute] | None:
        dals = self.resolve_dals(comp.class_name, comp.id)
        if dals is None:
            return None

        return [
            state_operations.AdjustableAttribute(
                self.configuration,
                self.session,
                dal,
                comp.attribute_name,
                label=dal.id,
            )
            for dal in dals if not self.is_dal_filtered(dal, comp.filters)
        ]