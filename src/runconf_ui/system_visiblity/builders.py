from runconf_ui import state_operations
from runconf_ui.system_visiblity.factories.attribute_operation_factory import AttributeOperationFactory
from runconf_ui.system_visiblity.factories.component_operation_factory import ComponentOperationFactory
from runconf_ui.system_visiblity.subsystem_registry import SubsystemRegistry

from conffwk import Configuration
from conffwk.dal import DalBase

from typing import List, Sequence


class SystemBuilder:
    """Builds a system operations tree."""
    def __init__(self, configuration: Configuration, session: DalBase):
        self.configuration = configuration
        self.session = session
        self.subsystems = SubsystemRegistry(configuration, session)

    def build(
        self,
        system_skeleton: dict,
    ) -> Sequence[state_operations.StateOperation]:

        system_name, props = next(iter(system_skeleton.items()))

        top_container = self._create_top_container(
            system_name,
            props.get("subsystem_dependent", False),
        )

        ops_list: List[state_operations.StateOperation] = [top_container]

        self._build_components(props.get("components", []), top_container, ops_list)
        self._build_attributes(props.get("attributes", []), top_container, ops_list)

        return ops_list

    # -------------------------

    def _create_top_container(self, label: str, dependent: bool):
        container_cls = (
            state_operations.StateOperationContainerAnd
            if dependent
            else state_operations.StateOperationContainerOr
        )

        return container_cls(self.configuration, self.session, label=label)

    def _build_components(self, components, top_container, ops_list):
        for comp in components:
            op = ComponentOperationFactory.create(
                self.configuration,
                self.session,
                comp,
            )
            if not op:
                continue

            ops_list.append(op)
            self.subsystems.attach(op, comp, top_container, ops_list)

    def _build_attributes(self, attributes, top_container, ops_list):
        for attr in attributes:
            container = AttributeOperationFactory.create(
                self.configuration,
                self.session,
                attr,
            )
            if not container:
                continue

            ops_list.append(container)
            self.subsystems.attach(container, attr, top_container, ops_list)
            
class OperationsTreeBuilder:
    """Builds full operations tree for visibility config."""

    def __init__(self, configuration: Configuration, session: DalBase):
        self.configuration = configuration
        self.session = session

    def build(self, skeleton: dict) -> dict:
        tree = {}

        for group_name, group_config in skeleton.items():
            tree[group_name] = {
                "label": group_config.get("label", group_name),
                "view_panel": group_config.get("view_panel", ""),
                "Systems": self._build_systems(group_config.get("Systems", [])),
            }

        return tree

    def _build_systems(self, systems: list):
        builder = SystemBuilder(self.configuration, self.session)
        return [builder.build(system) for system in systems]

