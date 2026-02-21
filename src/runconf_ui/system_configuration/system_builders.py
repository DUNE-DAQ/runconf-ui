"""
System builders for constructing SystemContainer objects
from structured configuration dataclasses.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.state_operations import (
    DisableOperation,
    StateOperation,
    StateOperationContainer,
    SystemContainer,
)
from runconf_ui.system_configuration.factories import (
    AdjustableOperationFactory,
    AttributeOperationFactory,
    ComponentOperationFactory,
    FactoryInterface,
    RelationshipOperationFactory,
)

from .config_dataclasses import (
    AdjustableAttributeData,
    DisableableSystemData,
)

# ============================================================
# Base Builder
# ============================================================

class SystemBuilder(ABC):
    """
    Generic system builder operating on structured dataclasses.
    """

    def __init__(
        self,
        configuration: Configuration,
        session: DalBase,
        factories: dict[str, FactoryInterface],
    ):
        self.configuration = configuration
        self.session = session
        self.factories = factories

    @abstractmethod
    def build(self, system_definition):
        """Build and return a SystemContainer."""
        ...

    # --------------------------------------------------------

    def _build_objects(
        self,
        objects: Iterable,
        system_container: SystemContainer,
        subsystem_dependent: bool,
        factory: FactoryInterface,
    ):
        """
        Uses a FactoryInterface to create operations from
        structured dataclass definitions.
        """
        for obj in objects:
            operations = factory.create(obj)
            if not operations:
                continue

            for operation in operations:
                self._add_to_system(
                    system_container,
                    obj,
                    subsystem_dependent,
                    operation,
                )

    # --------------------------------------------------------

    def _add_to_system(
        self,
        system_container: SystemContainer,
        system_definition,
        subsystem_dependent: bool,
        operation: StateOperation,
    ):
        """
        Adds an operation to the appropriate location
        inside the SystemContainer.
        """
        subclass_label = system_definition.system_label

        # If component should be separate, use operation label
        if (
            getattr(system_definition, "separate_system", False)
            and not isinstance(operation, StateOperationContainer)
            and not subclass_label
        ):
            subclass_label = operation.label

        # Add to subsystem if defined
        if subclass_label:
            system_container.add_to_subsystem(subclass_label, operation)
            return

        # Otherwise handle normally
        if subsystem_dependent and isinstance(operation, DisableOperation):
            system_container.add_controlled_object(operation)
        else:
            system_container.add_state_operation(operation)


# ============================================================
# Disableable Systems
# ============================================================

class DisableSystemBuilder(SystemBuilder):
    """
    Builder for DisableableSystemData objects.
    """

    def __init__(self, configuration: Configuration, session: DalBase):
        factory_args = (configuration, session)

        factories: dict[str, FactoryInterface] = {
            "components": ComponentOperationFactory(*factory_args),
            "attributes": AttributeOperationFactory(*factory_args),
            "relationships": RelationshipOperationFactory(*factory_args),
        }

        super().__init__(configuration, session, factories)

    # --------------------------------------------------------

    def build(self, system: DisableableSystemData) -> SystemContainer:
        """
        Build a SystemContainer from a DisableableSystemData instance.
        """

        container = SystemContainer(
            self.configuration,
            self.session,
            label=system.label if hasattr(system, "label") else "system",
        )

        for key, factory in self.factories.items():
            objects = getattr(system, key)            
            self._build_objects(
                objects,
                container,
                system.subsystem_dependent,
                factory,
            )

        return container


# ============================================================
# Adjustable Systems
# ============================================================

class AdjustableSystemBuilder(SystemBuilder):
    """
    Builder for AdjustableAttribute objects.
    """

    def __init__(self, configuration: Configuration, session: DalBase):
        factories: dict[str, FactoryInterface] = {
            "adjustable": AdjustableOperationFactory(configuration, session)
        }

        super().__init__(configuration, session, factories)

    # --------------------------------------------------------

    def build(self, attribute: AdjustableAttributeData) -> SystemContainer:
        """
        Build a SystemContainer from a single AdjustableAttribute.
        """

        container = SystemContainer(
            self.configuration,
            self.session,
            label=f"{attribute.attribute_name}_adjustable",
        )

        factory = self.factories["adjustable"]

        self._build_objects(
            [attribute],
            container,
            subsystem_dependent=False,
            factory=factory,
        )

        return container


# ============================================================
# Builder Factory
# ============================================================

def create_system_builder(
    label: str,
    configuration: Configuration,
    session: DalBase,
) -> SystemBuilder:
    """
    Factory function to create the appropriate SystemBuilder.
    """

    match label.lower():
        case "adjustable":
            return AdjustableSystemBuilder(configuration, session)
        case "disableable":
            return DisableSystemBuilder(configuration, session)
        case _:
            # No need for fancy error here, this will only be raised when developing
            raise ValueError(f"Builder '{label}' not recognised")