from runconf_ui import state_operations

from conffwk import Configuration
from conffwk.dal import DalBase

from typing import Optional

class ComponentOperationFactory:

    @staticmethod
    def create(
        configuration: Configuration,
        session: DalBase,
        component_config: dict,
    ) -> Optional[state_operations.DisableResource]:

        dal = configuration.get_dal(
            component_config["class"],
            component_config["id"],
        )

        if dal is None:
            return None

        return state_operations.DisableResource(configuration, session, dal)