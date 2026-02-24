"""
Unit tests for traversal.py.

Tests cover state computation, tree walking, labelled filtering,
disabled_children diagnostics, and build_index.
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

    def test_enabled_node_enabled_parent(self):
        parent = Group(strategy=all)
        child = leaf(True)
        parent.add(child)
        assert compute_state(child, parent) == State.ENABLED

    def test_enabled_node_disabled_parent(self):
        other = leaf(False)
        child = leaf(True)
        parent = Group(strategy=all)
        parent.add(other).add(child)
        assert compute_state(child, parent) == State.PARENT_DISABLED

    def test_disabled_node_disabled_parent_returns_disabled(self):
        """DISABLED takes precedence over PARENT_DISABLED."""
        other = leaf(False)
        child = leaf(False)
        parent = Group(strategy=all)
        parent.add(other).add(child)
        assert compute_state(child, parent) == State.DISABLED

    def test_dal_resource_disabled_returns_parent_disabled(self):
        child = leaf(True, dal_enabled=False)
        assert compute_state(child, None) == State.PARENT_DISABLED

    def test_dal_resource_disabled_with_disabled_parent_returns_disabled(self):
        """Node's own DISABLED state takes precedence."""
        child = leaf(False, dal_enabled=False)
        parent = Group(strategy=all)
        other = leaf(False)
        parent.add(other).add(child)
        assert compute_state(child, parent) == State.DISABLED

    def test_group_node_enabled(self):
        g = Group(strategy=all)
        g.add(leaf(True))
        assert compute_state(g, None) == State.ENABLED

    def test_group_node_disabled(self):
        g = Group(strategy=all)
        g.add(leaf(False))
        assert compute_state(g, None) == State.DISABLED

    def test_group_node_parent_disabled(self):
        other = leaf(False)
        child_group = Group(strategy=all)
        child_group.add(leaf(True))
        parent = Group(strategy=all)
        parent.add(other).add(child_group)
        assert compute_state(child_group, parent) == State.PARENT_DISABLED


# ---------------------------------------------------------------------------
# NodeStatus
# ---------------------------------------------------------------------------

class TestNodeStatus:

    def test_is_interactive_enabled(self):
        status = NodeStatus(node=leaf(), state=State.ENABLED, parent=None)
        assert status.is_interactive is True

    def test_is_interactive_disabled(self):
        status = NodeStatus(node=leaf(), state=State.DISABLED, parent=None)
        assert status.is_interactive is True

    def test_is_interactive_parent_disabled(self):
        status = NodeStatus(node=leaf(), state=State.PARENT_DISABLED, parent=None)
        assert status.is_interactive is False


# ---------------------------------------------------------------------------
# walk()
# ---------------------------------------------------------------------------

class TestWalk:

    def test_walk_single_leaf(self):
        leaf_test = leaf(True, label="a")
        statuses = list(walk(leaf_test))
        assert len(statuses) == 1
        assert statuses[0].node is leaf_test
        assert statuses[0].parent is None

    def test_walk_yields_root_first(self):
        root = Group("root", strategy=all)
        child = leaf(label="child")
        root.add(child)
        nodes = [s.node for s in walk(root)]
        assert nodes[0] is root

    def test_walk_depth_first(self):
        root = Group("root", strategy=all)
        child1 = leaf(label="c1")
        child2 = leaf(label="c2")
        grandchild = leaf(label="gc")

        sub = Group("sub", strategy=all)
        sub.add(grandchild)
        root.add(child1).add(sub).add(child2)

        nodes = [s.node for s in walk(root)]
        assert nodes == [root, child1, sub, grandchild, child2]

    def test_walk_sets_correct_parent(self):
        root = Group("root", strategy=all)
        child = leaf(label="child")
        root.add(child)

        statuses = {s.node: s for s in walk(root)}
        assert statuses[child].parent is root
        assert statuses[root].parent is None

    def test_walk_all_nodes_receive_state(self):
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
        root.add(leaf(label=""))   # anonymous
        root.add(leaf(label="x"))  # labelled
        labels = [s.node.label for s in labelled(root)]
        assert "" not in labels
        assert "x" in labels

    def test_all_labelled_nodes_included(self):
        root = Group("root", strategy=all)
        a = leaf(label="a")
        b = leaf(label="b")
        root.add(a).add(b)
        nodes = [s.node for s in labelled(root)]
        assert root in nodes
        assert a in nodes
        assert b in nodes

    def test_unlabelled_root_excluded(self):
        root = Group(label="", strategy=all)
        root.add(leaf(label="child"))
        nodes = [s.node for s in labelled(root)]
        assert root not in nodes


# ---------------------------------------------------------------------------
# disabled_children()
# ---------------------------------------------------------------------------

class TestDisabledChildren:
    def test_returns_voting_children_that_are_off(self):
        on  = leaf(True,  label="on")
        off = leaf(False, label="off")
        g = Group(strategy=all)
        g.add(on).add(off)
        result = disabled_child_nodes(g)
        assert result == [off]

    def test_ignores_non_voting_children(self):
        on_voter     = leaf(True,  label="voter")
        off_nonvoter = leaf(False, label="nonvoter")
        g = Group(strategy=all)
        g.add(on_voter, votes=True).add(off_nonvoter, votes=False)
        result = disabled_child_nodes(g)
        assert result == []

    def test_returns_empty_when_all_enabled(self):
        g = Group(strategy=all)
        g.add(leaf(True)).add(leaf(True))
        assert disabled_child_nodes(g) == []

    def test_returns_multiple_disabled_children(self):
        a = leaf(False, label="a")
        b = leaf(False, label="b")
        g = Group(strategy=all)
        g.add(a).add(b)
        assert set(disabled_child_nodes(g)) == {a, b}


# ---------------------------------------------------------------------------
# build_index()
# ---------------------------------------------------------------------------

class TestBuildIndex:
    def test_builds_flat_index(self):
        root = Group("root", strategy=all)
        a = leaf(label="a")
        b = leaf(label="b")
        root.add(a).add(b)
        index = build_index(root)
        assert index["root"] is root
        assert index["a"] is a
        assert index["b"] is b

    def test_includes_nested_nodes(self):
        root = Group("root", strategy=all)
        sub  = Group("sub",  strategy=any)
        deep = leaf(label="deep")
        sub.add(deep)
        root.add(sub)
        index = build_index(root)
        assert "deep" in index
        assert index["deep"] is deep

    def test_raises_on_duplicate_labels(self):
        root = Group("root", strategy=all)
        root.add(leaf(label="dup")).add(leaf(label="dup"))
        with pytest.raises(ValueError, match="dup"):
            build_index(root)

    def test_anonymous_nodes_excluded_from_index(self):
        root = Group("root", strategy=all)
        root.add(leaf(label=""))
        index = build_index(root)
        assert "" not in index

    def test_empty_tree(self):
        root = Group("root", strategy=all)
        index = build_index(root)
        assert index == {"root": root}

    def test_rebuild_is_idempotent(self):
        root = Group("root", strategy=all)
        root.add(leaf(label="a"))
        index1 = build_index(root)
        index2 = build_index(root)
        assert index1 == index2


# ---------------------------------------------------------------------------
# Integration: full tree state scenarios
# ---------------------------------------------------------------------------

class TestFullTreeScenarios:

    def test_parent_disabled_greys_out_enabled_child(self):
        """An enabled child under a disabled parent should be PARENT_DISABLED."""
        off_sibling = leaf(False, label="off")
        on_child    = leaf(True,  label="on")
        root = Group("root", strategy=all)
        root.add(off_sibling).add(on_child)

        statuses = {s.node: s for s in walk(root)}
        assert statuses[on_child].state == State.PARENT_DISABLED
        assert statuses[on_child].is_interactive is False

    def test_adjustable_leaf_parent_disabled_via_dal(self):
        """Adjustable leaf with DAL resource-disabled should be PARENT_DISABLED."""
        adjustable = leaf(True, label="rate", dal_enabled=False)
        root = Group("root", strategy=all)
        root.add(adjustable, votes=False, propagate=False)

        statuses = {s.node: s for s in walk(root)}
        assert statuses[adjustable].state == State.PARENT_DISABLED

    def test_adjustable_leaf_parent_group_disabled(self):
        """Adjustable leaf should be PARENT_DISABLED when parent group is off."""
        voter      = leaf(False, label="voter")
        adjustable = leaf(True,  label="rate")
        root = Group("root", strategy=all)
        root.add(voter, votes=True).add(adjustable, votes=False, propagate=False)

        statuses = {s.node: s for s in walk(root)}
        assert statuses[adjustable].state == State.PARENT_DISABLED

    def test_three_level_hierarchy(self):
        ru01 = leaf(True,  label="ru-01")
        ru02 = leaf(False, label="ru-02")
        tpg  = leaf(True,  label="tpg")

        crp4 = Group("CRP4", strategy=any)
        crp4.add(ru01).add(ru02)

        root = Group("TPC", strategy=all)
        root.add(crp4)
        root.add(tpg, votes=False, propagate=True)

        statuses = {s.node: s for s in walk(root)}

        # CRP4 is enabled (any: ru01 is on)
        assert statuses[crp4].state == State.ENABLED
        # ru01 is enabled
        assert statuses[ru01].state == State.ENABLED
        # ru02 is disabled (its own state)
        assert statuses[ru02].state == State.DISABLED
        # root is enabled (crp4 is its only voter)
        assert statuses[root].state == State.ENABLED
        # tpg is enabled (non-voting, parent is on)
        assert statuses[tpg].state == State.ENABLED