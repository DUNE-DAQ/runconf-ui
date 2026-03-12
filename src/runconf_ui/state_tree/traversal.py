"""
Traversal utilities and state computation for the state operation tree.

State is computed lazily during traversal — there is no cached state on nodes
themselves. Call walk() again after any set() to get fresh NodeStatus values.

The three states:

  ENABLED         — node is on, its DAL is resource-enabled, and its parent
                    (if any) is on.

  DISABLED        — node is internally off, and its parent (if any) is on.

  PARENT_DISABLED — the node is considered disabled due to an external
                    condition: either its parent group is off, or its
                    underlying DAL is resource-disabled in the session.
                    This takes precedence over the node's own internal state —
                    if the parent is off, children always report PARENT_DISABLED
                    regardless of their own stored value.
                    Renders as greyed-out and non-interactive in the UI.

Parent gating is checked first. A node's own internal state is only
consulted when its parent (if any) is enabled.
"""
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum, auto

from .nodes import Group, Leaf, Node

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class State(Enum):
    """The state of a node."""
    ENABLED         = auto()
    DISABLED        = auto()
    PARENT_DISABLED = auto()


@dataclass
class NodeStatus:
    """A full node status, carrying the node, its computed state, and its parent."""
    node:   Node
    state:  State
    parent: Group | None

    @property
    def is_interactive(self) -> bool:
        """False when the node is greyed out due to parent or DAL state."""
        return self.state != State.PARENT_DISABLED

    @property
    def is_enabled(self) -> bool:
        """True only when the node is fully enabled."""
        return self.state == State.ENABLED

    @property
    def path(self) -> str | None:
        if not self.node.label:
            return None
        if self.parent is None or not self.parent.label:
            return self.node.label or None
        return f"{self.parent.label}__{self.node.label}"

    @property
    def value(self):
        return self.node.get()

    @property
    def label(self):
        return self.node.label

    @property
    def tooltip(self) -> str:
        return self.node.tooltip

    def toggle(self) -> None:
        """Flip the node's state. No-op if the node is not interactive."""
        self.node.set(not self.node.get())
        self.refresh_state()

    def refresh_state(self) -> None:
        """Recompute state in place from live adapter values."""
        self.state = compute_state(self.node, self.parent)


# ---------------------------------------------------------------------------
# State computation
# ---------------------------------------------------------------------------

def compute_state(node: Node, parent: Group | None) -> State:
    """
    Compute the visible state of a node.

    Precedence (highest first):
      1. Parent gating — if the parent group is off, always PARENT_DISABLED.
      2. DAL resource state — if the underlying DAL is resource-disabled,
         PARENT_DISABLED (only checked for Leaf nodes).
      3. Node internal value — ENABLED or DISABLED.
    """
    # 1. Parent gating takes precedence over everything.
    if parent is not None and not parent.get():
        return State.PARENT_DISABLED

    # 2. Leaf DAL resource state.
    if isinstance(node, Leaf) and not node.adapter.dal_enabled():
        return State.PARENT_DISABLED

    # 3. Node's own internal value.
    if not node.get():
        return State.DISABLED

    return State.ENABLED


# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------

def walk(root: Node, parent: Group | None = None, _ancestor_disabled: bool = False):
    """
    Depth-first traversal of the node tree, yielding NodeStatus for every node.

    _ancestor_disabled is an internal parameter used during recursion to
    propagate PARENT_DISABLED down through the tree when an ancestor is off.
    It should not be passed by external callers.
    """
    state = compute_state(root, parent if not _ancestor_disabled else None)
    if _ancestor_disabled:
        state = State.PARENT_DISABLED
    yield NodeStatus(root, state, parent)

    if isinstance(root, Group):
        child_ancestor_disabled = _ancestor_disabled or state == State.PARENT_DISABLED
        for child, _, _ in root:
            yield from walk(child, parent=root, _ancestor_disabled=child_ancestor_disabled)


# ---------------------------------------------------------------------------
# Filtered views
# ---------------------------------------------------------------------------

def labelled(root: Node) -> Iterator[NodeStatus]:
    """Yields NodeStatus for all nodes with non-empty labels."""
    for status in walk(root):
        if status.node.label:
            yield status


def disabled_child_nodes(group: Group) -> list[Node]:
    """
    Returns the voting children that are causing this group to be disabled.
    Useful for diagnostic tooltips: "TPC is off because CRP4 is off."
    """
    return [n for n in group.voting_children if not n.get()]


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

def build_index(root: Node) -> dict[str, Node]:
    """
    Build a flat label->node mapping for O(1) lookup by label.
    Raises ValueError on duplicate labels.

    Call once after tree construction. Rebuild by calling again if the
    tree structure changes (only happens at startup).
    """
    index: dict[str, Node] = {}

    for status in labelled(root):
        label = status.node.label
        if label in index:
            raise ValueError(
                f"Duplicate label {label!r} in tree — all labelled nodes must be unique."
            )
        index[label] = status.node
    return index