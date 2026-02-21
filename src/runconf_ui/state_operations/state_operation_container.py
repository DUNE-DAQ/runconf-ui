from collections.abc import Sequence
from typing import Any

from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.exceptions import DuplicatedSubsystemException, SubsystemLabelError
from runconf_ui.state_operations import DisableOperation, StateOperation


class StateOperationContainer(DisableOperation):
    """
    Container object for MANY state operations.
    It will always be enable/disable-able with the enable/disable state being calculated
    from all DisableOperations stored in it.

    The _get_state method here is abstract; please use StateOperationContainerAnd or StateOperationContainerOr.
    """

    def __init__(
        self,
        configuration: Configuration,
        session: DalBase,
        label="",
        state_operations: Sequence[StateOperation[Any]] | None = None,
        controlled_objects: Sequence[DisableOperation] | None = None,
    ):
        super().__init__(configuration, session, label)
        self.object_registry: dict[str, StateOperation] = {}
        self._refresh_registry: bool = True
        self._nested_registry_cache: dict[str, StateOperation] | None = None

        self.state_operations = []
        if state_operations:
            for s in state_operations:
                self.add_state_operation(s)

        # Controlled objects are objects controlled wholly by the container but whose state
        # does not determine the state of the controller
        self.controlled_objects = []
        if controlled_objects:
            for c in controlled_objects:
                self.add_controlled_object(c)


    def add_state_operation(self, new_operation: StateOperation):
        """Add a StateOperation to the container."""
        if new_operation in self.state_operations:
            return

        if new_operation.label and new_operation.label in self.get_nested_registry():
            raise DuplicatedSubsystemException(
                f"Cannot have multiple objects with the same label "
                f"({new_operation.label}) {self.object_registry}!"
            )

        if isinstance(new_operation, DisableOperation):
            new_operation.add_top_level_container(self)

        self.state_operations.append(new_operation)

        if not new_operation.label:
            return

        self.object_registry[new_operation.label] = new_operation
        self._invalidate_registry_cache()

    def _set_state(self, state_val: bool):
        """Set the state of all objects contained in the container."""
        for obj in self.state_operations:
            obj.set_state(state_val)
        self.set_controlled_object_state()

    def get_disable_operations(self) -> Sequence[DisableOperation]:
        """Get all the disable operations."""
        return [a for a in self.state_operations if isinstance(a, DisableOperation)]

    def get_all_disable_states(self) -> Sequence[bool]:
        """Get the state of all disable operations."""
        return [o.get_internal_state() for o in self.get_disable_operations()]

    def add_controlled_object(self, controlled_object: DisableOperation):
        if controlled_object in self.controlled_objects:
            return

        # Bind it so we control its on/off-ness
        controlled_object.bind_state(self)
        self.controlled_objects.append(controlled_object)

    def set_controlled_object_state(self):
        """Set state of controlled objects."""
        for obj in self.controlled_objects:
            obj.set_internal_state(self.get_state())

    def get_nested_registry(self) -> dict[str, StateOperation]:
        """Recursively collect all nested objects stored with labels, with caching."""
        if not self._refresh_registry and self._nested_registry_cache is not None:
            return self._nested_registry_cache

        registry = self.object_registry.copy()

        for obj in self.state_operations:  # was object_registry.values()
            if isinstance(obj, StateOperationContainer):
                nested = obj.get_nested_registry()
                duplicates = registry.keys() & nested.keys()
                if duplicates:
                    raise KeyError(f"Duplicate registry keys detected: {duplicates}")
                registry.update(nested)

        self._nested_registry_cache = registry
        self._refresh_registry = False
        return registry

    def _invalidate_registry_cache(self):
        """Mark registry cache as dirty and propagate upwards."""
        self._refresh_registry = True
        self._nested_registry_cache = None

        for container in self._containers:
            if isinstance(container, StateOperationContainer):
                container._invalidate_registry_cache()

    def get_system(self, label: str):
        registry = self.get_nested_registry()
        if label not in registry:
            raise SubsystemLabelError(f"Cannot find {label} in nested labelled systems")
        return registry[label]


class StateOperationContainerAnd(StateOperationContainer):
    """State operation where the state is enabled iff ALL objects are enabled."""

    def _get_state(self):
        return all(self.get_all_disable_states())


class StateOperationContainerOr(StateOperationContainer):
    """State operation where the state is enabled if ANY object is enabled."""

    def _get_state(self):
        return any(self.get_all_disable_states())


class SystemContainer(StateOperationContainerAnd):
    """The TOP level container for a given system."""

    def __init__(
        self,
        configuration: Configuration,
        session: DalBase,
        label: str,
    ):
        super().__init__(configuration, session, label)
        self.subsystem_registry: list[str] = []

    def add_to_subsystem(self, subsystem_label: str, operator: StateOperation):
        """Add an operation to a named subsystem, creating it if it doesn't exist."""
        if subsystem_label in self.get_nested_registry() and subsystem_label not in self.subsystem_registry:
            raise DuplicatedSubsystemException(
                f"Cannot use the same label for a subsystem ({subsystem_label}) and a registered object"
            )

        if subsystem_label not in self.subsystem_registry:
            container = StateOperationContainerOr(
                self.configuration,
                self.session,
                subsystem_label,
            )
            self.subsystem_registry.append(subsystem_label)
            self.add_state_operation(container)

        subclass_container = self.object_registry[subsystem_label]

        if not isinstance(subclass_container, StateOperationContainer):
            raise SubsystemLabelError(
                f"Cannot add to {subsystem_label}. Subclasses must inherit from StateOperationContainer"
            )

        subclass_container.add_state_operation(operator)

    def get_subsystem(self, subsystem_label: str) -> StateOperationContainer:
        """Get a subsystem container by label. Case-sensitive."""
        if subsystem_label not in self.subsystem_registry:
            raise SubsystemLabelError(
                f"Cannot find {subsystem_label}. Valid systems are {self.subsystem_registry}"
            )
        return self.get_nested_registry()[subsystem_label]

    def get_system_state(self, subsystem_label: str) -> bool:
        """Get the current state of a named subsystem."""
        return self.get_subsystem(subsystem_label).get_state()