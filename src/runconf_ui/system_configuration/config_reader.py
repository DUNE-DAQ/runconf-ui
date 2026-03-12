"""
Configuration loading and assembly.

SystemConfig     — loads a YAML file and exposes typed dataclass skeletons.
ConfigAssembler  — turns skeletons into Group trees using the builders.
SystemConfigReader — public facade: load + assemble in one call.

AssembledConfig, AssembledGroup, AssembledSystem are the typed output
dataclasses consumed by the TUI layer.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.state_tree import Group, NodeStatus, walk
from runconf_ui.utils import get_logger

from .builders import AdjustableSystemBuilder, DisableSystemBuilder
from .dataclasses import (
    AdjustableGroupData,
    DisableableGroupData,
    YamlToSystemData,
)

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _natural_key(s: str):
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r'(\d+)', s)
    ]


def _node_sort_key(item: tuple[str, NodeStatus]):
    key, node = item
    return (
        0 if node.is_enabled else 1,
        _natural_key(key),
    )


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass()
class AssembledSystem:
    root:                Group
    display_full_system: bool

    def __post_init__(self):
        self.nodes: dict[str, NodeStatus] = {
            status.path: status
            for status in walk(self.root)
            if status.path is not None
            and (status.parent is None or bool(status.parent.label))
            and (self.display_full_system or status.parent is not None)
        }


@dataclass()
class AssembledGroup:
    id:         str
    label:      str
    systems:    list[AssembledSystem]
    view_panel: str = ""

    def __post_init__(self):
        self.nodes: dict[str, NodeStatus] = {}
        for system in self.systems:
            self.nodes.update(system.nodes)


@dataclass
class AssembledConfig:
    disableable: list[AssembledGroup]
    adjustable:  list[AssembledGroup]

    def __post_init__(self):
        self.disableable_nodes = {
            group.id: self._sorted_nodes(group.nodes)
            for group in self.disableable
        }
        self.adjustable_nodes = {
            group.id: self._sorted_nodes(group.nodes)
            for group in self.adjustable
        }
        self.all_nodes = {**self.adjustable_nodes, **self.disableable_nodes}

    def _sorted_nodes(self, nodes: dict[str, NodeStatus]) -> dict[str, NodeStatus]:
        return dict(sorted(nodes.items(), key=_node_sort_key))


# ---------------------------------------------------------------------------
# SystemConfig
# ---------------------------------------------------------------------------

class SystemConfig:
    """Loads a YAML file and exposes structured dataclass skeletons."""

    def __init__(self, path: Path):
        self.path = path
        raw = self._load(path)

        self._settings    = YamlToSystemData.build_settings(raw)
        self._disableable = YamlToSystemData.build_disableable_groups(
            raw.get("PanelOptions", {})
        )
        self._adjustable  = YamlToSystemData.build_adjustable_groups(
            raw.get("AdjustableAttributes", {})
        )

    @staticmethod
    def _load(path: Path) -> dict:
        with open(path) as f:
            return yaml.safe_load(f)

    @property
    def classes_to_show(self) -> list[str]:
        return self._settings.classes_to_show

    @property
    def disableable_skeleton(self) -> dict[str, DisableableGroupData]:
        return self._disableable

    @property
    def adjustable_skeleton(self) -> dict[str, AdjustableGroupData]:
        return self._adjustable


# ---------------------------------------------------------------------------
# ConfigAssembler
# ---------------------------------------------------------------------------

class ConfigAssembler:
    """Turns YAML skeletons into Group trees via the system builders."""

    def __init__(self, configuration: Configuration, session: DalBase):
        self.configuration = configuration
        self.session = session

    def assemble_disableable(
        self,
        skeleton: dict[str, DisableableGroupData],
    ) -> list[AssembledGroup]:
        builder = DisableSystemBuilder(self.configuration, self.session)

        assembled_groups = []
        for group_name, group_data in skeleton.items():
            systems = []
            for system_name, system_list in group_data.systems.items():
                for system_data in system_list:
                    # Build the tree once and reuse it — avoid running factories twice.
                    root = builder.build(system_data, label=system_name)
                    if not root.children:
                        continue
                    systems.append(AssembledSystem(
                        root=root,
                        display_full_system=system_data.display_full_system,
                    ))

            if not systems:
                continue

            assembled_groups.append(AssembledGroup(
                id=group_name,
                label=group_data.label or group_name,
                view_panel=group_data.view_panel,
                systems=systems,
            ))

        return assembled_groups

    def assemble_adjustable(
        self,
        skeleton: dict[str, AdjustableGroupData],
    ) -> list[AssembledGroup]:
        builder = AdjustableSystemBuilder(self.configuration, self.session)

        assembled_groups = []
        for group_name, group_data in skeleton.items():
            systems = []
            for system_name, attrs in group_data.systems.items():
                root = builder.build(attrs, label=system_name)
                if not root.children:
                    continue
                systems.append(AssembledSystem(
                    root=root,
                    display_full_system=False,
                ))

            if not systems:
                continue

            assembled_groups.append(AssembledGroup(
                id=group_name,
                label=group_data.label or group_name,
                view_panel="",
                systems=systems,
            ))

        return assembled_groups


# ---------------------------------------------------------------------------
# SystemConfigReader
# ---------------------------------------------------------------------------

class SystemConfigReader:
    """
    Public facade: loads a YAML config file and assembles it against a live
    conffwk configuration in one call.
    """

    def __init__(self, config_path: Path):
        get_logger().info(f"Reading config: {config_path}")
        self.config = SystemConfig(config_path)

    @property
    def classes_to_draw(self):
        """Classes to display in the global config tree."""
        return self.config.classes_to_show

    def assemble_config(
        self,
        configuration: Configuration,
        session_name: str,
    ) -> AssembledConfig:

        session   = configuration.get_dal("Session", session_name)
        assembler = ConfigAssembler(configuration, session)
        get_logger().info(f"Assembling: {session_name} in {repr(configuration)}")
        return AssembledConfig(
            disableable=assembler.assemble_disableable(self.config.disableable_skeleton),
            adjustable=assembler.assemble_adjustable(self.config.adjustable_skeleton),
        )