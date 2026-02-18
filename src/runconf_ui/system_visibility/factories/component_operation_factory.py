
from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui import state_operations


class ComponentOperationFactory:
    """Factory for creating DisableResource operations for components."""

    @staticmethod
    def create(configuration: Configuration, session: DalBase, comp: dict):
        object_class = comp["class"]
        object_id = comp.get("id", "")

        dals = []

        # If no id is specified or empty, take all DALs of this class
        if not object_id:
            dals = configuration.get_dals(object_class)
        else:
            dal = configuration.get_dal(object_class, object_id)
            if dal:
                dals = [dal]

        # Create DisableResource operations for all resolved DALs
        return [
            state_operations.DisableResource(configuration, session, dal)
            for dal in dals
        ]
