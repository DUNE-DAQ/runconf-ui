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
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

from .adapters.adapter import Adapter
from .node_state import NodeState


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class Node(ABC):
    """Base class for all tree nodes.

    Provides common interface for getting and setting node values.
    """

    def __init__(self, label: str = "", tooltip: str = ""):
        """Initialize a Node.

        :param label: Display name for the node (empty string = anonymous)
        :param tooltip: Hover text shown in the UI (defaults to label if empty)
        """
        self.label = label

        if not tooltip:
            tooltip = label

        self.tooltip = tooltip

    @abstractmethod
    def get(self) -> Any:
        """Get the value of the node.

        :returns: The node's current value
        """
        ...

    @abstractmethod
    def set(self, value: Any) -> None:
        """Set the value of the node.

        :param value: The new value for the node
        """
        ...


# ---------------------------------------------------------------------------
# Leaf
# ---------------------------------------------------------------------------


class Leaf(Node):
    """
    Wraps a single Adapter. The only node type that reads/writes conffwk.
    Reports its own raw adapter value; gating by parent is handled in traversal.
    """
    
    def __init__(self, adapter: Adapter, label: str = "", tooltip: str = ""):
        """Initialize a Leaf node.

        :param adapter: The Adapter that manages the underlying value
        :param label: Display name for the node
        :param tooltip: Hover text shown in the UI
        """
        super().__init__(label, tooltip)
        self.adapter = adapter

    def get(self) -> Any:
        """Get the adapter's value.

        :returns: The underlying adapter value
        """
        return self.adapter.get()

    def set(self, value: Any) -> None:
        """Set the adapter's value.

        :param value: The new value to set
        """
        self.adapter.set(value)


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------


class Group(Node):
    """
    Group of nodes
    """
    def __init__(
        self,
        label: str = "",
        tooltip: str = "",
    ):
        """Initialize a Group node.

        :param label: Display name for the group
        :param tooltip: Hover text shown in the UI
        :param strategy: Callable to aggregate child states (all or any)
        """
        super().__init__(label, tooltip)
        self.children: list[Node] = []

    # ------------------------------------------------------------------ #
    # Write path                                                           #
    # ------------------------------------------------------------------ #

    def add(
        self,
        node: Node,
    ) -> "Group":
        """Add a child node. Returns self for method chaining.

        :param node: The child node to add
        :returns: self for method chaining
        :rtype: Groupx
        """
        self.children.append(node)
        return self

    def at(self, *path: str) -> "Group":
        """Find or create a chain of named child Groups, returning the deepest.
        :param path: Hierarchical path labels for nested groups
        :returns: The deepest group in the created/found chain
        :rtype: Group
        """
        node = self
        for label in path:
            node = node._get_or_create_subgroup(label)
        return node

    def _get_or_create_subgroup(self, label: str) -> "Group":
        """Get or create a named subgroup.

        :param label: The label/name of the subgroup
        :returns: Existing or newly created subgroup
        :rtype: Group
        """
        for child in self.children:
            if isinstance(child, Group) and child.label == label:
                return child
        subgroup = Group(label=label)
        self.add(subgroup)
        return subgroup

    def set(self, value: bool | NodeState) -> None:
        """Propagate state to all children who can be toggled
        """
        for child in self.children:
            if isinstance(child.get(), NodeState):
                child.set(value)
    
    @property
    def top_level_leaves(self):
        return [c for c in self.children if isinstance(c, Leaf)]

    # ------------------------------------------------------------------ #
    # Read path                                                            #
    # ------------------------------------------------------------------ 
    def get(self) -> NodeState:
        """Get the aggregated state of all nodes."""
        child_states = [c.get() for c in self.children]
        
        if not child_states:
            return NodeState.DISABLED

        if NodeState.ERROR_STATE in child_states:
            return NodeState.ERROR_STATE


        top_states = [not NodeState.state_to_bool(i.get()) for i in self.top_level_leaves if isinstance(i.get(), NodeState)]

        if all(top_states) and top_states:
            return NodeState.DISABLED

        first_state = child_states[0]
        if all(s == first_state for s in child_states):
            return first_state

        if not isinstance(first_state, NodeState):
            return NodeState.ERROR_STATE

        if NodeState.ENABLED in child_states or NodeState.PARTIALLY_ENABLED in child_states:
            return NodeState.PARTIALLY_ENABLED

        return NodeState.ERROR_STATE

    # ------------------------------------------------------------------ #
    # Structural access                                                    #
    # ------------------------------------------------------------------ #

    def __iter__(self) -> Iterator[Node]:
        """Iterate over child nodes.

        :returns: Iterator of child node information tuples
        :rtype: Iterator[Node]
        """
        yield from self.children
