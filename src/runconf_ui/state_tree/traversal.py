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

from runconf_ui.state_tree.node_state import NodeState
from runconf_ui.utils.logging import get_logger

from .nodes import Group, Leaf, Node


@dataclass
class NodeStatus:
    """A full node status, carrying the node, its computed state, and its parent."""

    node: Node
    state: NodeState
    parent: Group | None

    @property
    def is_interactive(self) -> bool:
        """False when the node is greyed out due to parent or DAL state."""
        if self.parent is None:
            return True
        
        if not self.parent.top_level_groups:
            return True
        
        return NodeState.state_to_bool(self.parent.get()) 

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

        Only works when is_interactive is True (not PARENT_DISABLED).
        """
        if self.state != NodeState.ERROR_STATE:    
            self.node.set(not NodeState.state_to_bool(self.state))

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


def compute_state(node: Node, parent: Group | None) -> NodeState:
    """Compute the visible state of a node.

    Precedence (highest first):
      1. Parent gating — if the parent group is off, always PARENT_DISABLED.
      2. DAL resource state — if the underlying DAL is resource-disabled,
         PARENT_DISABLED (only checked for Leaf nodes).
      3. Node internal value — ENABLED or DISABLED.

    :param node: The node to compute state for
    :param parent: The parent group, if any
    :returns: The computed state
    :rtype: State
    """
    parent_gated = (
        parent is not None
        and not NodeState.state_to_bool(parent.get())
        and (all(not NodeState.state_to_bool(s.get()) for s in parent.top_level_groups) if parent.top_level_groups else True)
    )
    dal_disabled = isinstance(node, Leaf) and not node.adapter.dal_enabled()

    if parent_gated or dal_disabled:
        return NodeState.PARENT_DISABLED

    return node.get()

# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------


def walk(root: Node, parent: Group | None = None, _ancestor_state: NodeState = NodeState.ENABLED):
    """Depth-first traversal of the node tree, yielding NodeStatus for every node.

    Yields NodeStatus objects containing the state of each node in the tree.
    _ancestor_disabled is an internal parameter used during recursion to
    propagate PARENT_DISABLED down through the tree when an ancestor is off.

    :param root: The root node to start traversal from
    :param parent: The parent group (internal use)
    :param _ancestor_disabled: Whether an ancestor is disabled (internal use)
    :returns: Iterator of NodeStatus objects
    :rtype: Iterator[NodeStatus]
    """
    state = compute_state(root, parent if not _ancestor_state else None)
    if not NodeState.state_to_bool(_ancestor_state):
        state = NodeState.PARENT_DISABLED

    # We can also set the state here
    yield NodeStatus(root, state, parent)

    if isinstance(root, Group):
        child_ancestor_disabled = NodeState.state_to_bool(_ancestor_state) or NodeState.state_to_bool(state)
        for child in root:
            yield from walk(
                child, parent=root, _ancestor_state=NodeState.bool_to_state(child_ancestor_disabled)
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


def disabled_child_nodes(group: Group) -> list[Node]:
    """Get voting children that are causing the group to be disabled.

    Useful for diagnostic tooltips like "TPC is off because CRP4 is off."

    :param group: The group to check
    :returns: List of disabled voting child nodes
    :rtype: list[Node]
    """
    return [n for n in group.children if not NodeState.state_to_bool(n.get())]


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
