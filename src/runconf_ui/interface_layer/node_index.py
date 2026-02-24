import re
from dataclasses import dataclass
from enum import Enum, auto

from runconf_ui.state_tree import NodeStatus, labelled
from runconf_ui.system_configuration.config_reader import AssembledConfig, AssembledGroup

_UNSAFE = re.compile(r"[^a-zA-Z0-9_-]")


def _slugify(s: str) -> str:
    return _UNSAFE.sub("_", s)


def make_widget_id(group_label: str, system_label: str, node_label: str) -> str:
    """
    Stable, Textual-safe widget ID encoding the full path:
        <group_label>__<system_label>__<node_label>
    e.g. "detector__Readout__ru-01"

    Single source of truth — call this wherever an ID needs to be produced
    or resolved. Never construct IDs by hand.
    """
    return "__".join(_slugify(s) for s in (group_label, system_label, node_label))


# ---------------------------------------------------------------------------
# Entry types
# ---------------------------------------------------------------------------

class NodeKind(Enum):
    DISABLE    = auto()  # bool toggle — maps to enable/disable buttons
    ADJUSTABLE = auto()  # raw value get/set — maps to input widgets


@dataclass(frozen=True)
class IndexEntry:
    widget_id: str
    status:    NodeStatus
    kind:      NodeKind

    @property
    def node(self):
        return self.status.node

    def refresh(self) -> 'IndexEntry':
        """Return a new IndexEntry with recomputed NodeStatus."""
        return IndexEntry(
            widget_id=self.widget_id,
            status=self.status.refresh(),
            kind=self.kind,
        )


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

NodeIndex    = dict[str, IndexEntry]
GroupedIndex = dict[str, dict[str, IndexEntry]]


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _collect(group_label: str, systems, kind: NodeKind) -> dict[str, IndexEntry]:
    """
    Collect a flat widget_id -> IndexEntry mapping from a list of
    AssembledSystems, tagging each entry with the given NodeKind.
    """
    flat: dict[str, IndexEntry] = {}
    for system in systems:
        for status in labelled(system.root):
            wid = make_widget_id(group_label, system.root.label, status.node.label)
            if wid in flat:
                raise ValueError(
                    f"Duplicate widget_id {wid!r} in group '{group_label}'"
                )
            flat[wid] = IndexEntry(widget_id=wid, status=status, kind=kind)
    return flat


def build_disable_index(assembled: AssembledConfig) -> GroupedIndex:
    """
    { group_label: { widget_id: IndexEntry, ... }, ... }
    Only covers disableable groups.
    """
    grouped: GroupedIndex = {}
    for group in assembled.disableable:
        flat = _collect(group.label, group.systems, NodeKind.DISABLE)
        if flat:
            grouped[group.label] = flat
    return grouped


def build_adjustable_index(assembled: AssembledConfig) -> GroupedIndex:
    """
    { group_label: { widget_id: IndexEntry, ... }, ... }
    Only covers adjustable groups.
    """
    grouped: GroupedIndex = {}
    for group in assembled.adjustable:
        flat = _collect(group.label, group.systems, NodeKind.ADJUSTABLE)
        if flat:
            grouped[group.label] = flat
    return grouped


def build_node_index(assembled: AssembledConfig) -> NodeIndex:
    """
    Flat widget_id -> IndexEntry mapping across ALL groups (disable + adjustable).
    Used for O(1) lookup by widget_id regardless of kind.
    """
    flat: NodeIndex = {}
    for grouped in (build_disable_index(assembled), build_adjustable_index(assembled)):
        for inner in grouped.values():
            flat.update(inner)
    return flat


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def toggle_node(index: NodeIndex, widget_id: str) -> IndexEntry:
    """
    Toggle a DISABLE node and return its refreshed IndexEntry.
    Raises TypeError if called on an ADJUSTABLE node.
    """
    entry = index[widget_id]
    if entry.kind is not NodeKind.DISABLE:
        raise TypeError(
            f"toggle_node called on ADJUSTABLE node {widget_id!r} — use set_value instead"
        )
    entry.status.toggle()
    return entry.refresh()


def get_value(index: NodeIndex, widget_id: str):
    """
    Get the current raw value of an ADJUSTABLE node.
    Raises TypeError if called on a DISABLE node.
    """
    entry = index[widget_id]
    if entry.kind is not NodeKind.ADJUSTABLE:
        raise TypeError(
            f"get_value called on DISABLE node {widget_id!r} — use toggle_node instead"
        )
    return entry.node.get()


def set_value(index: NodeIndex, widget_id: str, value) -> IndexEntry:
    """
    Set the raw value of an ADJUSTABLE node and return its refreshed IndexEntry.
    Raises TypeError if called on a DISABLE node.
    """
    entry = index[widget_id]
    if entry.kind is not NodeKind.ADJUSTABLE:
        raise TypeError(
            f"set_value called on DISABLE node {widget_id!r} — use toggle_node instead"
        )
    entry.node.set(value)
    return entry.refresh()