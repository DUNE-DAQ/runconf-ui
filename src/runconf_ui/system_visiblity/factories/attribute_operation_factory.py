from typing import Optional

from runconf_ui import state_operations
from runconf_ui.utils import get_class_from_segment

from conffwk import Configuration
from conffwk.dal import DalBase

class AttributeOperationFactory:
    @staticmethod
    def create(
        configuration: Configuration,
        session: DalBase,
        attr_config: dict,
    ) -> Optional[state_operations.StateOperationContainerOr]:

        dal_list = []

        for segment in attr_config.get("segments", []):
            dals = get_class_from_segment(
                configuration,
                segment,
                attr_config["class"],
            )
            if dals:
                dal_list.extend(dals)

        if not dal_list:
            return None

        operations = [
            state_operations.DisableAttribute(
                configuration,
                session,
                dal,
                attr_config["id"],
                attr_config.get("enabled_value", True),
                attr_config.get("disabled_value", False),
            )
            for dal in dal_list
        ]

        return state_operations.StateOperationContainerOr(
            configuration,
            session,
            operations,
        )