from collections.abc import Sequence

from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.state_operations.state_operation import DisableOperation, StateOperation


class StateOperationContainer(DisableOperation):
    """
    Container object for MANY state operations.
    It will always be enable/disable-able with the enable/disable state being calculated
    from all DisableOperations stored in it

    The get state method here is abstract, please use StateOperationContainerAnd or StateOperationContainerOr

    """

    def __init__(
        self,
        configuration: Configuration,
        session: DalBase,
        contained_resources: list[StateOperation] | None = None,
        label="",
    ):

        super().__init__(configuration, session, label)

        self.contained_operations: list[StateOperation] = (
            contained_resources if contained_resources else []
        )

    def add_state_operation(self, new_operation: StateOperation):
        """
        Add a StateOperation to the container
        """
        if new_operation in self.contained_operations:
            return
        self.contained_operations.append(new_operation)

    def set_state(self, state_val: bool):
        """
        Set the state of all objects contained in the container
        """
        for obj in self.contained_operations:
            obj.set_state(state_val)

    def get_disable_operations(self) -> Sequence[DisableOperation]:
        """
        Get all the disable operations
        """
        return [a for a in self.contained_operations if isinstance(a, DisableOperation)]

    def get_all_disable_states(self) -> Sequence[bool]:
        """
        Get the state of all disable operations
        """
        return [o.get_state() for o in self.get_disable_operations()]


class StateOperationContainerAnd(StateOperationContainer):
    """
    State operation where the state is enabled iff ALL objects are enabled
    """

    def get_state(self):
        return all(self.get_all_disable_states())


class StateOperationContainerOr(StateOperationContainer):
    """
    State operation where the state is enabled if any object is enabled
    """

    def get_state(self):
        return any(self.get_all_disable_states())
