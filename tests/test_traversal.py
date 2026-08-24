"""
Unit tests for traversal.py.

Tests cover state computation, walk, labelled, disabled_child_nodes,
and build_index. Full-tree scenario tests are handled in test_integration.py.
"""

import pytest

from runconf_ui.state_tree import (
    Group,
    Leaf,
    NodeStatus,
    build_index,
    compute_state,
    disabled_child_nodes,
    labelled,
    walk,
)
from runconf_ui.state_tree.node_state import NodeState

# ---------------------------------------------------------------------------
# Stub adapter
# ---------------------------------------------------------------------------


class StubAdapter:
    def __init__(self, value: NodeState|bool = True, dal_enabled: bool = True):
        if isinstance(value, bool):
            value = NodeState.bool_to_state(value)
        
        self._value = value
        self._dal_enabled = dal_enabled

    def get(self):
        return self._value

    def set(self, value):
        if not isinstance(value, NodeState):
            value  = NodeState.bool_to_state(value)
        self._value = value

    def dal_enabled(self):
        return self._dal_enabled


def leaf(value: bool = True, label: str = "", dal_enabled: bool=True) -> Leaf:
    return Leaf(StubAdapter(value, dal_enabled), label=label)  # type: ignore


# ---------------------------------------------------------------------------
# compute_state
# ---------------------------------------------------------------------------


class TestComputeState:
    def test_enabled_node_no_parent(self):
        assert compute_state(leaf(NodeState.ENABLED), None) == NodeState.ENABLED

    def test_disabled_node_no_parent(self):
        assert compute_state(leaf(NodeState.DISABLED), None) == NodeState.DISABLED


    def test_disabled_node_with_disabled_parent_returns_parent_disabled(self):
        # Parent gating takes precedence — node's own DISABLED is not visible
        # when the parent is already off.
        child = leaf(False)
        parent = Group()
        parent.add(leaf(False)).add(child)
        assert compute_state(child, parent) == NodeState.PARENT_DISABLED

    def test_dal_resource_disabled_returns_parent_disabled(self):
        g = Group()
        lf = leaf(True, dal_enabled=False)
        g.add(lf)
        
        assert (
            compute_state(lf, g) == NodeState.PARENT_DISABLED
        )

    def test_group_node_enabled(self):
        g = Group()
        g.add(leaf(NodeState.ENABLED))
        assert compute_state(g, None) == NodeState.ENABLED

    def test_group_node_disabled(self):
        g = Group()
        g.add(leaf(False))
        assert compute_state(g, None) == NodeState.DISABLED

    def test_group_node_parent_disabled(self):
        child_group = Group()
        child_group.add(leaf(False))
        parent = Group()
        parent.add(leaf(False)).add(child_group)
        assert compute_state(child_group, parent) == NodeState.PARENT_DISABLED


# ---------------------------------------------------------------------------
# NodeStatus
# ---------------------------------------------------------------------------


class TestNodeStatus:
    def test_is_interactive_for_enabled_and_disabled(self):
        assert (
            NodeStatus(node=leaf(), state=NodeState.ENABLED, parent=None).is_interactive
            is True
        )
        assert (
            NodeStatus(node=leaf(), state=NodeState.DISABLED, parent=None).is_interactive
            is True
        )

    def test_not_interactive_when_parent_disabled(self):
        parent = Group()
        child = leaf(False)
        parent.add(child)
        parent.at("subgroup").add(leaf(False))

        assert (
            NodeStatus(
                node=child, state=NodeState.DISABLED, parent=parent
            ).is_interactive
            is False
        )
        
        assert (
            NodeStatus(
                node=parent, state=NodeState.DISABLED, parent=None
            ).is_interactive
            is True
        )
        
# ---------------------------------------------------------------------------
# walk()
# ---------------------------------------------------------------------------


class TestWalk:
    def test_yields_root_first_then_depth_first(self):
        root = Group("root")
        c1 = leaf(label="c1")
        sub = Group("sub")
        gc = leaf(label="gc")
        c2 = leaf(label="c2")
        sub.add(gc)
        root.add(c1).add(sub).add(c2)
        assert [s.node for s in walk(root)] == [root, c1, sub, gc, c2]

    def test_sets_correct_parent(self):
        root = Group("root")
        child = leaf(label="child")
        root.add(child)
        statuses = {s.node: s for s in walk(root)}
        assert statuses[child].parent is root
        assert statuses[root].parent is None

    def test_all_nodes_receive_state(self):
        root = Group("root")
        root.add(leaf(True, label="a")).add(leaf(False, label="b"))
        for status in walk(root):
            assert isinstance(status.state, NodeState)


# ---------------------------------------------------------------------------
# labelled()
# ---------------------------------------------------------------------------


class TestLabelled:
    def test_anonymous_nodes_excluded(self):
        root = Group("root")
        root.add(leaf(label=""))
        root.add(leaf(label="x"))
        labels = [s.node.label for s in labelled(root)]
        assert "" not in labels
        assert "x" in labels

    def test_unlabelled_root_excluded(self):
        root = Group(label="")
        root.add(leaf(label="child"))
        assert root not in [s.node for s in labelled(root)]


# ---------------------------------------------------------------------------
# disabled_child_nodes()
# ---------------------------------------------------------------------------


class TestDisabledChildNodes:
    def test_returns_voting_children_that_are_off(self):
        on = leaf(True, label="on")
        off = leaf(False, label="off")
        g = Group()
        g.add(on).add(off)
        assert disabled_child_nodes(g) == [off]

    def test_empty_when_all_enabled(self):
        g = Group()
        g.add(leaf(True)).add(leaf(True))
        assert disabled_child_nodes(g) == []


# ---------------------------------------------------------------------------
# build_index()
# ---------------------------------------------------------------------------


class TestBuildIndex:
    def test_flat_and_nested_nodes_indexed(self):
        root = Group("root")
        sub = Group("sub")
        deep = leaf(label="deep")
        a = leaf(label="a")
        sub.add(deep)
        root.add(a).add(sub)
        index = build_index(root)
        assert set(index.keys()) == {"root", "a", "sub", "deep"}

    def test_raises_on_duplicate_labels(self):
        root = Group("root")
        root.add(leaf(label="dup")).add(leaf(label="dup"))
        with pytest.raises(ValueError, match="dup"):
            build_index(root)

    def test_anonymous_nodes_excluded(self):
        root = Group("root")
        root.add(leaf(label=""))
        assert "" not in build_index(root)

    def test_rebuild_is_idempotent(self):
        root = Group("root")
        root.add(leaf(label="a"))
        assert build_index(root) == build_index(root)
