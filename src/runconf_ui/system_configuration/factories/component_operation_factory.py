from runconf_ui.state_operations import DisableResource

from ..config_dataclasses import DisableElementData
from .factory_interface import FactoryInterface


class ComponentOperationFactory(FactoryInterface):
    def create(self, comp: DisableElementData) -> list[DisableResource] | None:
        dals = self.resolve_dals(comp.class_name, comp.id)
        if dals is None:
            return None

        separate = comp.each_component_separate
        return [
            DisableResource(
                self.configuration,
                self.session,
                dal,
                dal.id if separate else "",
            )
            for dal in dals if not self.is_dal_filtered(dal, comp.filters)
        ]