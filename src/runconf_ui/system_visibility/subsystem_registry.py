
from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui import state_operations


class SubsystemRegistry:
    """Manages subsystem containers and grouping logic."""
    SUBSYSTEM_LABEL = "__SUBSYSTEMS__"
    TOP_SYSTEM_LABEL = "__TOPSYSTEMS__"


    def __init__(self, configuration: Configuration, session: DalBase):
        self.configuration = configuration
        self.session = session
        self._containers: dict[str, state_operations.StateOperationContainerOr] = {}

    def _generate_extra_container(self, top_level_container, subsystem_container, label):
        '''
        For systems with the logic "if all subsystems are off switch me off" we need to keep the subsystems
        in an extra bit of OR logic. This ensures the we can have the system turn off if the subsystems switch off
        '''
        sub_cont = None
        for c in top_level_container.contained_operations:
            if c.label != label:
                continue
            sub_cont = c
            break
        
        if sub_cont is None:
            sub_cont = state_operations.StateOperationContainerOr(
                self.configuration,
                self.session,
                [],
                label=label
            )
            top_level_container.add_state_operation(sub_cont)

        sub_cont.add_state_operation(subsystem_container)

        
    def add_to_subsystem_container(self, top_level_container, subsystem_container):
        self._generate_extra_container(top_level_container,
                                       subsystem_container,
                                       self.SUBSYSTEM_LABEL)

    def add_to_topsystem_container(self, top_level_container, object_container):
        self._generate_extra_container(top_level_container, 
                                       object_container,
                                       self.TOP_SYSTEM_LABEL)

    

    def attach(
        self,
        operation,
        config_entry: dict,
        top_level_container,
        ops_list: list,
    ):
        separate = config_entry.get("separate_system", False)
        label = config_entry.get("system_label", "")
        subsystem_dep = config_entry.get("subsystem_dependent", True)

        if not (separate and label and subsystem_dep):
            top_level_container.add_state_operation(operation)
            return
        if not (separate and label and not subsystem_dep):
            self.add_to_topsystem_container(top_level_container, operation)

        if label not in self._containers:
            container = state_operations.StateOperationContainerOr(
                self.configuration,
                self.session,
                label=label,
            )
            self._containers[label] = container

            # We keep ALL subsystems in there own little container
            if subsystem_dep:
                self.add_to_subsystem_container(top_level_container, container)
            else:
                top_level_container.add_state_operation(container)

            ops_list.append(container)

        self._containers[label].add_state_operation(operation)