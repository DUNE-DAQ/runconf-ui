"""
Traversal utilities and state computation for the state operation tree.

State is computed lazily during traversal — there is no cached state on nodes
themselves. Call walk() again after any set() to get fresh NodeStatus values.

The three states:

  INCLUDED         — node is on, its DAL is ExcludableEntity-included, and its parent
                    (if any) is on.

  EXCLUDED        — node is internally off, and its parent (if any) is on.

  PARENT_EXCLUDED — the node is considered excluded due to an external
                    condition: either its parent group is off, or its
                    underlying DAL is ExcludableEntity-excluded in the session.
                    This takes precedence over the node's own internal state —
                    if the parent is off, children always report PARENT_EXCLUDED
                    regardless of their own stored value.
                    Renders as greyed-out and non-interactive in the UI.

Parent gating is checked first. A node's own internal state is only
consulted when its parent (if any) is included.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum, auto

from runconf_ui.utils.logging import get_logger

from .nodes import Group, Leaf, Node

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class State(Enum):
    """The state of a node."""

    INCLUDED = auto()
    EXCLUDED = auto()
    PARENT_EXCLUDED = auto()


@dataclass
class NodeStatus:
    """A full node status, carrying the node, its computed state, and its parent."""

    node: Node
    state: State
    parent: Group | None

    @property
    def is_interactive(self) -> bool:
        """False when the node is greyed out due to parent or DAL state."""
        return self.state != State.PARENT_EXCLUDED

    @property
    def is_included(self) -> bool:
        """True only when the node is fully included."""
        return self.state == State.INCLUDED

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
        """Flip the node's state. No-op if the node is not interactive.

        Only works when is_interactive is True (not PARENT_EXCLUDED).
        """
        self.node.set(not self.node.get())
        get_logger().debug(f"Toggling {self.label}")

        self.refresh_state()

    def refresh_state(self) -> None:
        """Recompute state in place from live adapter values.

        Updates the state attribute based on current node and parent values.
        """
        self.state = compute_state(self.node, self.parent)
        get_logger().debug(f"{self.label} now in state {self.state}")


# ---------------------------------------------------------------------------
# State computation
# ---------------------------------------------------------------------------


def compute_state(node: Node, parent: Group | None) -> State:
    """Compute the visible state of a node.

    Precedence (highest first):
      1. Parent gating — if the parent group is off, always PARENT_EXCLUDED.
      2. DAL ExcludableEntity state — if the underlying DAL is ExcludableEntity-excluded,
         PARENT_EXCLUDED (only checked for Leaf nodes).
      3. Node internal value — INCLUDED or EXCLUDED.

    :param node: The node to compute state for
    :param parent: The parent group, if any
    :returns: The computed state
    :rtype: State
    """
    # 1. Parent gating takes precedence over everything.
    if parent is not None and not parent.get():
        return State.PARENT_EXCLUDED

    # 2. Leaf DAL ExcludableEntity state.
    if isinstance(node, Leaf) and not node.adapter.dal_included():
        return State.PARENT_EXCLUDED

    # 3. Node's own internal value.
    if not node.get():
        return State.EXCLUDED

    return State.INCLUDED


# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------


def walk(root: Node, parent: Group | None = None, _ancestor_excluded: bool = False):
    """Depth-first traversal of the node tree, yielding NodeStatus for every node.

    Yields NodeStatus objects containing the state of each node in the tree.
    _ancestor_excluded is an internal parameter used during recursion to
    propagate PARENT_EXCLUDED down through the tree when an ancestor is off.

    :param root: The root node to start traversal from
    :param parent: The parent group (internal use)
    :param _ancestor_excluded: Whether an ancestor is excluded (internal use)
    :returns: Iterator of NodeStatus objects
    :rtype: Iterator[NodeStatus]
    """
    state = compute_state(root, parent if not _ancestor_excluded else None)
    if _ancestor_excluded:
        state = State.PARENT_EXCLUDED

    # We can also set the state here
    yield NodeStatus(root, state, parent)

    if isinstance(root, Group):
        child_ancestor_excluded = _ancestor_excluded or state == State.PARENT_EXCLUDED
        for child, _, _ in root:
            yield from walk(
                child, parent=root, _ancestor_excluded=child_ancestor_excluded
            )


# ---------------------------------------------------------------------------
# Filtered views
# ---------------------------------------------------------------------------


def labelled(root: Node) -> Iterator[NodeStatus]:
    """Yield NodeStatus for all nodes with non-empty labels.

    :param root: The root node to traverse
    :returns: Iterator of NodeStatus for labelled nodes only
    :rtype: Iterator[NodeStatus]
    """
    for status in walk(root):
        if status.node.label:
            yield status


def excludable_child_nodes(group: Group) -> list[Node]:
    """Get voting children that are causing the group to be excluded.

    Useful for diagnostic tooltips like "TPC is off because CRP4 is off."

    :param group: The group to check
    :returns: List of excluded voting child nodes
    :rtype: list[Node]
    """
    return [n for n in group.voting_children if not n.get()]


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


def build_index(root: Node) -> dict[str, Node]:
    """Build a flat label->node mapping for O(1) lookup by label.

    Raises ValueError on duplicate labels. Call once after tree construction.
    Rebuild by calling again if the tree structure changes.

    :param root: The root node to index
    :returns: Dictionary mapping node labels to node objects
    :rtype: dict[str, Node]
    :raises ValueError: If duplicate labels are found in the tree
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
