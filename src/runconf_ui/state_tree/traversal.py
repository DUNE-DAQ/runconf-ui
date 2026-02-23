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
"""

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum, auto

from .nodes import Group, Leaf, Node


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class State(Enum):
    ENABLED         = auto()
    DISABLED        = auto()
    PARENT_DISABLED = auto()


@dataclass(frozen=True)
class NodeStatus:
    node:   Node
    state:  State
    parent: Group | None

    @property
    def is_interactive(self) -> bool:
        """False when the node is greyed out due to parent or DAL state."""
        return self.state != State.PARENT_DISABLED


# ---------------------------------------------------------------------------
# State computation
# ---------------------------------------------------------------------------

def compute_state(node: Node, parent: Group | None) -> State:
    """
    Compute the visible state of a node given its parent.
    Pure function — does not modify any node.

    Checks in order:
      1. Node's own get() — if False, DISABLED regardless of anything else.
      2. Parent group state — if parent is off, PARENT_DISABLED.
      3. DAL resource state (Leaf nodes only) — if the underlying DAL is
         resource-disabled in the session, PARENT_DISABLED.
         This covers adjustable nodes whose DAL may be disabled independently
         of the tree structure, and DisableAttribute nodes whose DAL may be
         resource-disabled without that being reflected in the attribute value.
    """
    own = node.get()

    if not own:
        return State.DISABLED

    if parent is not None and not parent.get():
        return State.PARENT_DISABLED

    if isinstance(node, Leaf) and not node.adapter.dal_enabled():
        return State.PARENT_DISABLED

    return State.ENABLED


# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------

def walk(root: Node) -> Iterator[NodeStatus]:
    """
    Depth-first traversal of the full tree.
    Yields NodeStatus for every node, root first.
    """
    yield NodeStatus(node=root, state=compute_state(root, None), parent=None)
    yield from _walk(root, parent=None)


def _walk(node: Node, parent: Group | None) -> Iterator[NodeStatus]:
    if isinstance(node, Group):
        for child, _, _ in node:
            yield NodeStatus(
                node=child,
                state=compute_state(child, parent=node),
                parent=node,
            )
            yield from _walk(child, parent=node)


# ---------------------------------------------------------------------------
# Filtered views
# ---------------------------------------------------------------------------

def labelled(root: Node) -> Iterator[NodeStatus]:
    """Yields NodeStatus for all nodes with non-empty labels."""
    for status in walk(root):
        if status.node.label:
            yield status


def disabled_children(group: Group) -> list[Node]:
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