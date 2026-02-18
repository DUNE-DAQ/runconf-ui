from runconf_ui import state_operations
from typing import Dict, List

from conffwk import Configuration
from conffwk.dal import DalBase

class SubsystemRegistry:
    """Manages subsystem containers and grouping logic."""

    def __init__(self, configuration: Configuration, session: DalBase):
        self.configuration = configuration
        self.session = session
        self._containers: Dict[str, state_operations.StateOperationContainerOr] = {}

    def attach(
        self,
        operation,
        config_entry: dict,
        top_level_container,
        ops_list: List,
    ):
        separate = config_entry.get("separate_system", False)
        label = config_entry.get("system_label", "")

        if not (separate and label):
            top_level_container.add_state_operation(operation)
            return

        if label not in self._containers:
            container = state_operations.StateOperationContainerOr(
                self.configuration,
                self.session,
                label=label,
            )
            self._containers[label] = container
            ops_list.append(container)

        self._containers[label].add_state_operation(operation)