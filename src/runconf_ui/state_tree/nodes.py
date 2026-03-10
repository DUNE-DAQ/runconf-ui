"""
Tree nodes for representing detector state hierarchy.

There are two node types:

  Leaf  — wraps a single Adapter; the only nodes that touch conffwk.
  Group — aggregates children; state is all() or any() of voting children.

Parent-child relationships are owned entirely by the parent. Children have
no reference to their parent. State propagation is top-down only: a Group
gates its children's visible state — if the group is disabled, all children
report disabled regardless of their own stored state. This gating is computed
in traversal.py, not here.

Every node has:
  label:   str — display name for rendering and index lookup.
                 Empty string means anonymous (not shown in the UI).
  tooltip: str — text shown on hover in the UI. Empty string means no tooltip.

Children are stored as _Child entries carrying two flags:

  votes: bool      — does this child's state contribute to the parent's
                     aggregated state?
                     False for adjustable nodes and controlled-but-non-voting
                     components.

  propagate: bool  — should Group.set() reach this child?
                     False for adjustable nodes, whose values are set directly
                     via their adapter and must not receive a bool from the
                     enable/disable tree.
                     True for all disable nodes, voting or not.

The two flags are independent:

  votes=True,  propagate=True  — normal voting disable child (default)
  votes=False, propagate=True  — gated by parent, doesn't influence it
                                 (replaces the old controlled_objects mechanism)
  votes=False, propagate=False — adjustable child: organisationally grouped
                                 here but fully independent of enable/disable
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from .adapters.adapter import Adapter

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Node(ABC):
    """Base class for all tree nodes."""

    def __init__(self, label: str = "", tooltip: str = ""):
        self.label = label

        if not tooltip:
            tooltip = label

        self.tooltip = tooltip

    @abstractmethod
    def get(self) -> Any:
        '''Get the value of the node'''
        
    @abstractmethod
    def set(self, value: Any) -> None:
        '''Set the value of the node'''
        

# ---------------------------------------------------------------------------
# Leaf
# ---------------------------------------------------------------------------

class Leaf(Node):
    """
    Wraps a single Adapter. The only node type that reads/writes conffwk.
    Reports its own raw adapter value; gating by parent is handled in traversal.
    """

    def __init__(self, adapter: Adapter, label: str = "", tooltip: str = ""):
        super().__init__(label, tooltip)
        self.adapter = adapter

    def get(self) -> Any:
        return self.adapter.get()

    def set(self, value: Any) -> None:
        self.adapter.set(value)


# ---------------------------------------------------------------------------
# Child entry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Child:
    node:      Node
    votes:     bool
    propagate: bool


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------

class Group(Node):
    """
    Aggregates the state of its children.

    strategy is a callable over an iterable of bools:
      all — enabled iff every voting child is enabled (AND semantics)
      any — enabled if any voting child is enabled  (OR semantics)

    Children added with votes=False do not contribute to the aggregated state
    but are still gated by it (they appear disabled when the parent is off).

    Children added with propagate=False are not reached by set() — used for
    adjustable nodes whose values are managed directly via their adapter.

    Usage:
        group = Group("TPC", strategy=all)
        group.add(segment_leaf)
        group.add(tpg_leaf, votes=False)

        # Adjustable node — grouped here but independent of enable/disable:
        group.add(rate_leaf, votes=False, propagate=False)

        # Fluent subsystem creation:
        group.at("CRP4").add(crp4_leaf).add(crp4_tpg, votes=False)
        group.at("CRP4", "TPG").add(deep_leaf)
    """

    def __init__(
        self,
        label: str = "",
        tooltip: str = "",
        strategy: Callable[[Iterable[bool]], bool] = all,
    ):
        super().__init__(label, tooltip)
        self.strategy = strategy
        self._children: list[_Child] = []

    # ------------------------------------------------------------------ #
    # Write path                                                           #
    # ------------------------------------------------------------------ #

    def add(
        self,
        node: Node,
        votes: bool = True,
        propagate: bool = True,
    ) -> 'Group':
        """
        Add a child node. Returns self for chaining:
            group.add(a).add(b, votes=False)

        votes=True,  propagate=True  — normal disable child (default)
        votes=False, propagate=True  — controlled-but-non-voting disable child
        votes=False, propagate=False — adjustable child
        """
        self._children.append(_Child(node=node, votes=votes, propagate=propagate))
        return self

    def at(self, *path: str) -> 'Group':
        """
        Find or create a chain of named child Groups, returning the deepest.
        Creates any missing intermediate groups with strategy=any.

            root.at("CRP4")         — one level
            root.at("CRP4", "TPG")  — two levels, creating both if absent
        """
        node = self
        for label in path:
            node = node._get_or_create_subgroup(label)
        return node

    def _get_or_create_subgroup(self, label: str) -> 'Group':
        for child in self._children:
            if isinstance(child.node, Group) and child.node.label == label:
                return child.node
        subgroup = Group(label=label, strategy=any)
        self.add(subgroup, votes=True, propagate=True)
        return subgroup

    def set(self, value: bool) -> None:
        """
        Propagate state to all children where propagate=True.
        Adjustable nodes (propagate=False) are never touched.
        """ 
        for child in self._children:
            if child.propagate:
                child.node.set(value)

    # ------------------------------------------------------------------ #
    # Read path                                                            #
    # ------------------------------------------------------------------ #

    def get(self) -> bool:
        """
        Aggregated state of voting children.
        Returns True vacuously when there are no voting children.
        """
        voting = self.voting_children
        if not voting:
            return True
        return self.strategy(child.get() for child in voting)

    def gated_get(self, child: Node) -> bool:
        """
        Return the visible state of a direct child, gated by this group.
        If this group is disabled the child reports disabled regardless of
        its own stored state.
        """
        if not self.get():
            return False
        return child.get()

    # ------------------------------------------------------------------ #
    # Structural access                                                    #
    # ------------------------------------------------------------------ #

    def __iter__(self) -> Iterator[tuple[Node, bool, bool]]:
        """Iterate over (child, votes, propagate) triples."""
        for c in self._children:
            yield c.node, c.votes, c.propagate

    @property
    def voting_children(self) -> list[Node]:
        return [c.node for c in self._children if c.votes]

    @property
    def children(self) -> list[Node]:
        return [c.node for c in self._children]