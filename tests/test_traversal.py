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
    State,
    build_index,
    compute_state,
    disabled_child_nodes,
    labelled,
    walk,
)


# ---------------------------------------------------------------------------
# Stub adapter
# ---------------------------------------------------------------------------

class StubAdapter:
    def __init__(self, value: bool = True, dal_enabled: bool = True):
        self._value = value
        self._dal_enabled = dal_enabled

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def dal_enabled(self):
        return self._dal_enabled


def leaf(value: bool = True, label: str = "", dal_enabled: bool = True) -> Leaf:
    return Leaf(StubAdapter(value, dal_enabled=dal_enabled), label=label)


# ---------------------------------------------------------------------------
# compute_state
# ---------------------------------------------------------------------------

class TestComputeState:

    def test_enabled_node_no_parent(self):
        assert compute_state(leaf(True), None) == State.ENABLED

    def test_disabled_node_no_parent(self):
        assert compute_state(leaf(False), None) == State.DISABLED

    def test_enabled_node_with_disabled_parent_returns_parent_disabled(self):
        child = leaf(True)
        parent = Group(strategy=all)
        parent.add(leaf(False)).add(child)
        assert compute_state(child, parent) == State.PARENT_DISABLED

    def test_disabled_node_with_disabled_parent_returns_parent_disabled(self):
        # Parent gating takes precedence — node's own DISABLED is not visible
        # when the parent is already off.
        child = leaf(False)
        parent = Group(strategy=all)
        parent.add(leaf(False)).add(child)
        assert compute_state(child, parent) == State.PARENT_DISABLED

    def test_dal_resource_disabled_returns_parent_disabled(self):
        assert compute_state(leaf(True, dal_enabled=False), None) == State.PARENT_DISABLED

    def test_group_node_enabled(self):
        g = Group(strategy=all)
        g.add(leaf(True))
        assert compute_state(g, None) == State.ENABLED

    def test_group_node_disabled(self):
        g = Group(strategy=all)
        g.add(leaf(False))
        assert compute_state(g, None) == State.DISABLED

    def test_group_node_parent_disabled(self):
        child_group = Group(strategy=all)
        child_group.add(leaf(True))
        parent = Group(strategy=all)
        parent.add(leaf(False)).add(child_group)
        assert compute_state(child_group, parent) == State.PARENT_DISABLED


# ---------------------------------------------------------------------------
# NodeStatus
# ---------------------------------------------------------------------------

class TestNodeStatus:

    def test_is_interactive_for_enabled_and_disabled(self):
        assert NodeStatus(node=leaf(), state=State.ENABLED,  parent=None).is_interactive is True
        assert NodeStatus(node=leaf(), state=State.DISABLED, parent=None).is_interactive is True

    def test_not_interactive_when_parent_disabled(self):
        assert NodeStatus(node=leaf(), state=State.PARENT_DISABLED, parent=None).is_interactive is False


# ---------------------------------------------------------------------------
# walk()
# ---------------------------------------------------------------------------

class TestWalk:

    def test_yields_root_first_then_depth_first(self):
        root = Group("root", strategy=all)
        c1 = leaf(label="c1")
        sub = Group("sub", strategy=all)
        gc = leaf(label="gc")
        c2 = leaf(label="c2")
        sub.add(gc)
        root.add(c1).add(sub).add(c2)
        assert [s.node for s in walk(root)] == [root, c1, sub, gc, c2]

    def test_sets_correct_parent(self):
        root = Group("root", strategy=all)
        child = leaf(label="child")
        root.add(child)
        statuses = {s.node: s for s in walk(root)}
        assert statuses[child].parent is root
        assert statuses[root].parent is None

    def test_all_nodes_receive_state(self):
        root = Group("root", strategy=all)
        root.add(leaf(True, label="a")).add(leaf(False, label="b"))
        for status in walk(root):
            assert isinstance(status.state, State)


# ---------------------------------------------------------------------------
# labelled()
# ---------------------------------------------------------------------------

class TestLabelled:

    def test_anonymous_nodes_excluded(self):
        root = Group("root", strategy=all)
        root.add(leaf(label=""))
        root.add(leaf(label="x"))
        labels = [s.node.label for s in labelled(root)]
        assert "" not in labels
        assert "x" in labels

    def test_unlabelled_root_excluded(self):
        root = Group(label="", strategy=all)
        root.add(leaf(label="child"))
        assert root not in [s.node for s in labelled(root)]


# ---------------------------------------------------------------------------
# disabled_child_nodes()
# ---------------------------------------------------------------------------

class TestDisabledChildNodes:

    def test_returns_voting_children_that_are_off(self):
        on = leaf(True, label="on")
        off = leaf(False, label="off")
        g = Group(strategy=all)
        g.add(on).add(off)
        assert disabled_child_nodes(g) == [off]

    def test_ignores_non_voting_children(self):
        g = Group(strategy=all)
        g.add(leaf(True), votes=True)
        g.add(leaf(False), votes=False)
        assert disabled_child_nodes(g) == []

    def test_empty_when_all_enabled(self):
        g = Group(strategy=all)
        g.add(leaf(True)).add(leaf(True))
        assert disabled_child_nodes(g) == []


# ---------------------------------------------------------------------------
# build_index()
# ---------------------------------------------------------------------------

class TestBuildIndex:

    def test_flat_and_nested_nodes_indexed(self):
        root = Group("root", strategy=all)
        sub  = Group("sub",  strategy=any)
        deep = leaf(label="deep")
        a    = leaf(label="a")
        sub.add(deep)
        root.add(a).add(sub)
        index = build_index(root)
        assert set(index.keys()) == {"root", "a", "sub", "deep"}

    def test_raises_on_duplicate_labels(self):
        root = Group("root", strategy=all)
        root.add(leaf(label="dup")).add(leaf(label="dup"))
        with pytest.raises(ValueError, match="dup"):
            build_index(root)

    def test_anonymous_nodes_excluded(self):
        root = Group("root", strategy=all)
        root.add(leaf(label=""))
        assert "" not in build_index(root)

    def test_rebuild_is_idempotent(self):
        root = Group("root", strategy=all)
        root.add(leaf(label="a"))
        assert build_index(root) == build_index(root)