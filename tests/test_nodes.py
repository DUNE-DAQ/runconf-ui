"""
Unit tests for nodes.py.

Uses simple stub adapters — no conffwk dependency.
"""

from runconf_ui.state_tree import Group, Leaf, NodeState

# ---------------------------------------------------------------------------
# Stub adapter
# ---------------------------------------------------------------------------


class StubAdapter:
    def __init__(self, value: NodeState|bool = True):
        if isinstance(value, bool):
            value = NodeState.bool_to_state(value)
        
        self._value = value
        self._dal_enabled = True

    def get(self):
        return self._value

    def set(self, value):
        if not isinstance(value, NodeState):
            value  = NodeState.bool_to_state(value)
        self._value = value

    def dal_enabled(self):
        return self._dal_enabled


def leaf(value: bool = True, label: str = "") -> Leaf:
    return Leaf(StubAdapter(value), label=label)  # type: ignore


# ---------------------------------------------------------------------------
# Leaf
# ---------------------------------------------------------------------------
class TestLeaf:
    def test_get_and_set(self):
        n = leaf(True)
        assert n.get() == NodeState.ENABLED
        n.set(False)
        assert n.get() == NodeState.DISABLED

    def test_label(self):
        assert leaf(label="my-leaf").label == "my-leaf"


# ---------------------------------------------------------------------------
# Group — get() aggregation
# ---------------------------------------------------------------------------


class TestGroupGet:
    def test_group_true(self):
        g = Group()
        g.add(leaf(True)).add(leaf(True))
        assert g.get() == NodeState.ENABLED

    def test_disabled(self):
        g = Group()
        g.add(leaf(False)).add(leaf(False))
        assert g.get() == NodeState.DISABLED

    def test_partial_enable(self):
        g = Group()
        g.add(leaf(False)).add(leaf(True))
        assert g.get() == NodeState.PARTIALLY_ENABLED


    def test_empty_group_vacuously_disabled(self):
        assert Group().get() == NodeState.DISABLED


# ---------------------------------------------------------------------------
# Group — set() propagation
# ---------------------------------------------------------------------------


class TestGroupSet:
    def test_set_propagates_to_voting_and_propagate_true_children(self):
        voting = leaf(True)
        controlled = leaf(True)
        g = Group()
        g.add(voting)
        g.add(controlled)
        g.set(False)
        assert voting.get() == NodeState.DISABLED
        assert controlled.get() == NodeState.DISABLED

    def test_set_propagates_through_nested_groups(self):
        inner_leaf = leaf(True)
        inner = Group()
        inner.add(inner_leaf)
        outer = Group()
        outer.add(inner)
        outer.set(False)
        assert inner_leaf.get() == NodeState.DISABLED


# ---------------------------------------------------------------------------
# Group — at() subsystem creation
# ---------------------------------------------------------------------------


class TestGroupAt:
    def test_at_creates_and_reuses_subgroup(self):
        root = Group("root", )
        sub1 = root.at("CRP4")
        sub2 = root.at("CRP4")
        assert isinstance(sub1, Group)
        assert sub1 is sub2

    def test_at_creates_nested_path(self):
        root = Group("root", )
        deep = root.at("CRP4", "TPG")
        assert deep.label == "TPG"
        assert root.at("CRP4").at("TPG") is deep

    def test_at_subgroup_participates_in_parent_state(self):
        root = Group("root", )
        root.at("CRP4").add(leaf(True))
        assert root.get() == NodeState.ENABLED


# ---------------------------------------------------------------------------
# Group — structural accessors
# ---------------------------------------------------------------------------


class TestGroupStructure:
    def test_children_and_voting_children(self):
        g = Group()
        a, b = leaf(), leaf()
        g.add(a).add(b)
        assert g.children == [a, b]

    def test_iter_yields_node_votes_propagate(self):
        g = Group()
        a, b, c = leaf(), leaf(), leaf()
        g.add(a)
        g.add(b)
        g.add(c)
        assert list(g) == [a,b,c]