"""
Rich rendering of runconf-ui trees and summaries from plain data.

The backend builds trees as ``DrawItem``s (see rich_utils); the gRPC client
rebuilds the same ``DrawItem``s from protobuf messages. Both render through the
functions here, so the TUI looks identical whichever backend it talks to.

Deliberately free of DAQ dependencies (conffwk etc.) so a remote frontend can use it.

Colour scheme:
  green  — INCLUDED
  red    — EXCLUDED
  grey46 — PARENT_EXCLUDED (node is internally on but parent group is off,
           or the underlying DAL is ExcludableEntity-excluded in the session)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rich.tree import Tree

from runconf_ui.state_tree.traversal import State

_COLOURS: dict[State, str] = {
    State.INCLUDED: "green",
    State.EXCLUDED: "red",
    State.PARENT_EXCLUDED: "grey46",
}

NO_CONFIG_INFO = "No Config Selected"
NO_CONFIG_TREE = "No Config Loaded"


@dataclass
class DrawItem:
    """One entry in a drawn tree.

    :param label: Plain text label (no markup)
    :param state: Node state; None for plain entries such as relationship names
    :param children: Child entries, in display order
    :param source: Backend object this entry was built from (backend side only)
    """

    label: str
    state: State | None = None
    children: list[DrawItem] = field(default_factory=list)
    source: Any = None


@dataclass
class ConfigInfo:
    """Summary of the loaded configuration shown above the panels."""

    daq_version: str | None
    apparatus: str
    config_file: str | None
    current_file: str | None
    session_name: str | None


def format_state_label(label: str, state: State) -> str:
    """Format a label with colour and state annotation for Rich rendering."""
    colour = _COLOURS[state]
    return f"[bold {colour}]{label}[/]   [dim {colour}]{state.name.lower()}[/]"


def add_items(branch: Tree, items: list[DrawItem]) -> None:
    """Add entries under ``branch``: stateful ones coloured by state, others in cyan."""
    for item in items:
        label = (
            f"[cyan]{item.label}"
            if item.state is None
            else format_state_label(item.label, item.state)
        )
        add_items(branch.add(label), item.children)


def render_node_tree(root: DrawItem) -> Tree:
    """Render one system's node hierarchy (root label highlighted)."""
    tree = Tree(format_state_label(f"[bold green]{root.label}[/]", root.state))
    add_items(tree, root.children)
    return tree


def render_panel_tree(title: str, systems: list[DrawItem]) -> Tree:
    """Render a view panel: a title with one subtree per system."""
    tree = Tree(title)
    tree.children.extend(render_node_tree(s) for s in systems)
    return tree


def render_config_tree(session_name: str | None, items: list[DrawItem]) -> Tree:
    """Render the configuration (DAL) tree under its session."""
    if session_name is None:
        return Tree(NO_CONFIG_TREE)
    tree = Tree(f"[bold green]{session_name}")
    add_items(tree, items)
    return tree


def format_info_text(info: ConfigInfo | None) -> str:
    """Summary text for the file-select panel."""
    if info is None:
        return NO_CONFIG_INFO
    return (
        f"      [bold green]DAQ Version[/bold green]:  [deep_pink4]{info.daq_version}[/deep_pink4]\n"
        f"      [bold green]Apparatus[/bold green]:  [deep_pink4]{info.apparatus}[/deep_pink4]\n"
        f"      [bold green]DAQ Config[/bold green]: [deep_pink4]{info.config_file}[/deep_pink4]\n"
        f"      [bold green]Current Config File[/bold green]:  [deep_pink4]{info.current_file}[/deep_pink4]\n"
        f"      [bold green]Session in Config[/bold green]:  [deep_pink4]{info.session_name}[/deep_pink4]\n"
    )
