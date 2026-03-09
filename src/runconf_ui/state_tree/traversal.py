"""
Traversal utilities and state computation for the state operation tree.

State is computed lazily during traversal — there is no cached state on nodes
themselves. Call walk() again after any set() to get fresh NodeStatus values.

The three states:

  ENABLED         — node is on, its DAL is resource-enabled, and its parent
                    (if any) is on.

  DISABLED        — node is internally off.

  PARENT_DISABLED — node is internally on but is considered disabled due to
                    an external condition: either its parent group is off, or
                    its underlying DAL is resource-disabled in the session.
                    Renders as greyed-out and non-interactive in the UI.
                    The two causes are not distinguished at the State level;
                    use disabled_children() or adapter.dal_enabled() directly
                    if diagnostic detail is needed.

If a node is both internally disabled and parent/DAL-disabled, DISABLED is
returned — the node's own state is the more informative signal.

This code ALL assumes just 1 layer of nesting!
"""
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum, auto

from .nodes import Group, Leaf, Node

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class State(Enum):
    '''The state of a node'''
    ENABLED         = auto()  # Node is enabled
    DISABLED        = auto()  # Node is disabled
    PARENT_DISABLED = auto()  # Node's parent is disabled

@dataclass
class NodeStatus:
    '''A full node status, carrying the node, its computed state, and its parent.'''
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
        """The full path to this node, e.g. "CRP4__TPC".
        __ denotes nesting. This notation is used for compatibility
        with Textual's ID system, which only allows flat strings.
        """
        if not self.node.label:
            return None
        
        if self.parent is None:
            return self.node.label or None
        return f"{self.parent.label}__{self.node.label}"

    def toggle(self) -> None:
        """
        Flip the node's state and return a fresh NodeStatus reflecting the
        result. No-op (returns self) if the node is not interactive.
        """
        self.node.set(not self.node.get())
        self.refresh_state()

    def refresh_state(self) -> None:
        """
        Update the node's state in place, recomputing from the live adapter values.
        """
        self.state = compute_state(self.node, self.parent)


# ---------------------------------------------------------------------------
# State computation
# ---------------------------------------------------------------------------
def compute_state(node: Node, parent: Group | None) -> State:
    """
    Compute the visible state of a node, immutable snapshot.

    Precedence:
      1. Parent gating (highest)
      2. Node internal value
      3. Leaf DAL state
    """
    # Parent gating: parent aggregate off → PARENT_DISABLED
    if parent is not None and not parent.get():  
        return State.PARENT_DISABLED

    # Node internal flag (for disableable voting nodes)
    if isinstance(node, Leaf) or isinstance(node, Group):
        if not node.get():
            return State.DISABLED

    # Leaf DAL gating
    if isinstance(node, Leaf) and not node.adapter.dal_enabled():
        return State.PARENT_DISABLED

    # Fully enabled
    return State.ENABLED

# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------

def walk(root: Node, parent: Group | None = None, ancestor_disabled=False):
    state = compute_state(root, parent if not ancestor_disabled else None)
    if ancestor_disabled:
        state = State.PARENT_DISABLED
    yield NodeStatus(root, state, parent)

    if isinstance(root, Group):
        for child, _, _ in root:
            child_ancestor_disabled = ancestor_disabled or state == State.PARENT_DISABLED
            yield from walk(child, parent=root, ancestor_disabled=child_ancestor_disabled)


#             yield from _walk(child, parent=node, ancestor_disabled=child_ancestor_disabled)


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