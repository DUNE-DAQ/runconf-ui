import yaml
from pathlib import Path
from typing import Dict, List, Sequence

from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.utils import get_class_from_segment
from runconf_ui import state_operations

# ============================================================
# CONFIG LAYER
# ============================================================

class VisibilityConfig:
    """Loads and exposes structured visibility configuration."""

    def __init__(self, path: Path):
        self._raw = self._load(path)

    @staticmethod
    def _load(path: Path) -> dict:
        with open(path, "r") as f:
            return yaml.safe_load(f)

    @property
    def classes_to_show(self) -> str:
        return self._raw.get("Settings", {}).get("classes_to_show", "")

    @property
    def adjustable_skeleton(self) -> dict:
        return self._raw.get("AdjustableAttributes", {})

    @property
    def disableable_skeleton(self) -> dict:
        return self._raw.get("PanelOptions", {})


# ============================================================
# SUBSYSTEM REGISTRY (for disableable objects)
# ============================================================

class SubsystemRegistry:
    """Manages subsystem containers and grouping logic."""

    def __init__(self, configuration: Configuration, session: DalBase):
        self.configuration = configuration
        self.session = session
        self._containers: Dict[str, state_operations.StateOperationContainerOr] = {}

    def attach(self, operation, config_entry: dict, top_level_container, ops_list: List):
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


# ============================================================
# COMPONENT AND ATTRIBUTE FACTORIES (disableable objects)
# ============================================================

class ComponentOperationFactory:

    @staticmethod
    def create(configuration: Configuration, session: DalBase, comp: dict):
        dal = configuration.get_dal(comp["class"], comp["id"])
        if dal is None:
            return None
        return state_operations.DisableResource(configuration, session, dal)


class AttributeOperationFactory:

    @staticmethod
    def create(configuration: Configuration, session: DalBase, attr: dict):
        dal_list = []
        for segment in attr.get("segments", []):
            dals = get_class_from_segment(configuration, segment, attr["class"])
            if dals:
                dal_list.extend(dals)
        if not dal_list:
            return None

        attribute_ops = [
            state_operations.DisableAttribute(
                configuration,
                session,
                dal,
                attr["id"],
                attr.get("enabled_value", True),
                attr.get("disabled_value", False),
            )
            for dal in dal_list
        ]
        return state_operations.StateOperationContainerOr(configuration, session, attribute_ops)


# ============================================================
# SYSTEM BUILDER (disableable)
# ============================================================

class SystemBuilder:
    """Builds a disableable system tree."""

    def __init__(self, configuration: Configuration, session: DalBase):
        self.configuration = configuration
        self.session = session
        self.subsystems = SubsystemRegistry(configuration, session)

    def build(self, system_skeleton: dict) -> Sequence[state_operations.StateOperation]:
        system_name, props = next(iter(system_skeleton.items()))
        top_container = self._create_top_container(system_name, props.get("subsystem_dependent", False))

        ops_list: List[state_operations.StateOperation] = [top_container]
        self._build_components(props.get("components", []), top_container, ops_list)
        self._build_attributes(props.get("attributes", []), top_container, ops_list)

        return ops_list

    def _create_top_container(self, label: str, dependent: bool):
        container_cls = state_operations.StateOperationContainerAnd if dependent else state_operations.StateOperationContainerOr
        return container_cls(self.configuration, self.session, label=label)

    def _build_components(self, components, top_container, ops_list):
        for comp in components:
            op = ComponentOperationFactory.create(self.configuration, self.session, comp)
            if not op:
                continue
            ops_list.append(op)
            self.subsystems.attach(op, comp, top_container, ops_list)

    def _build_attributes(self, attributes, top_container, ops_list):
        for attr in attributes:
            container = AttributeOperationFactory.create(self.configuration, self.session, attr)
            if not container:
                continue
            ops_list.append(container)
            self.subsystems.attach(container, attr, top_container, ops_list)


# ============================================================
# OPERATIONS TREE BUILDER (disableable)
# ============================================================

class OperationsTreeBuilder:
    """Builds disableable operations tree."""

    def __init__(self, configuration: Configuration, session: DalBase):
        self.configuration = configuration
        self.session = session

    def build(self, skeleton: dict) -> dict:
        tree = {}
        for group_name, group_config in skeleton.items():
            tree[group_name] = {
                "label": group_config.get("label", group_name),
                "view_panel": group_config.get("view_panel", ""),
                "Systems": [SystemBuilder(self.configuration, self.session).build(s) for s in group_config.get("Systems", [])]
            }
        return tree


# ============================================================
# DAL RESOLVER AND ADJUSTABLE OPERATIONS (adjustable attributes)
# ============================================================

class DalResolver:
    """Resolves DAL objects from AdjustableAttributes YAML entries."""

    @staticmethod
    def resolve(configuration: Configuration, config: dict):
        if "object_id" in config:
            dal = configuration.get_dal(config["object_class"], config["object_id"])
            return [dal] if dal else []

        dals = configuration.get_dals(config["object_class"])
        filters = config.get("filters", [])
        for f in filters:
            attr = f["attribute"]
            values = f["values"]
            dals = [d for d in dals if hasattr(d, attr) and getattr(d, attr) not in values]

        return dals


class AdjustableOperationFactory:

    @staticmethod
    def create(configuration: Configuration, session: DalBase, dal: DalBase, config: dict):
        label = getattr(dal, "description", "")
        return state_operations.AdjustableAttribute(configuration, session, dal, config["attribute_name"], label=label)


class AdjustableSystemBuilder:
    """Builds adjustable attribute operations for one system entry."""

    def __init__(self, configuration: Configuration, session: DalBase, system_config: dict):
        self.configuration = configuration
        self.session = session
        self.system_config = system_config

    def build(self):
        dals = DalResolver.resolve(self.configuration, self.system_config)
        operations = [AdjustableOperationFactory.create(self.configuration, self.session, dal, self.system_config) for dal in dals]

        return {
            "operations": operations,
            "unit_label": self.system_config.get("unit_label", ""),
            "tooltip": self.system_config.get("tooltip", ""),
            "is_hex": self.system_config.get("is_hex", False),
        }


class AdjustableGroupBuilder:
    """Builds one adjustable attribute group."""

    def __init__(self, configuration: Configuration, session: DalBase, group_name: str, group_config: dict):
        self.configuration = configuration
        self.session = session
        self.group_name = group_name
        self.group_config = group_config

    def build(self) -> dict:
        return {
            "label": self.group_config.get("label", self.group_name),
            "Systems": [AdjustableSystemBuilder(self.configuration, self.session, s).build() for s in self.group_config.get("Systems", [])]
        }


class AdjustableTreeBuilder:
    """Builds the AdjustableAttributes tree."""

    def __init__(self, configuration: Configuration, session: DalBase):
        self.configuration = configuration
        self.session = session

    def build(self, skeleton: dict) -> dict:
        tree = {}
        for group_name, group_config in skeleton.items():
            tree[group_name] = AdjustableGroupBuilder(self.configuration, self.session, group_name, group_config).build()
        return tree


# ============================================================
# FACADE
# ============================================================
class VisibilityConfigReader:
    """Facade coordinating disableable and adjustable operations trees."""

    def __init__(self, config_path: Path):
        self.config = VisibilityConfig(config_path)

    def generate_operations_tree(self, configuration: Configuration, session_name: str):
        session = configuration.get_dal("Session", session_name)

        disable_builder = OperationsTreeBuilder(configuration, session)
        adjustable_builder = AdjustableTreeBuilder(configuration, session)

        return {
            "disableable": disable_builder.build(self.config.disableable_skeleton),
            "adjustable": adjustable_builder.build(self.config.adjustable_skeleton),
        }