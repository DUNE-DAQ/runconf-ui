"""
Unit tests for nodes.py.

Uses simple stub adapters — no conffwk dependency.
"""

from runconf_ui.state_tree import Group, Leaf

# ---------------------------------------------------------------------------
# Stub adapter
# ---------------------------------------------------------------------------


class StubAdapter:
    def __init__(self, value: bool = True):
        self._value = value
        self._dal_enabled = True

    def get(self):
        return self._value

    def set(self, value):
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
        assert n.get() is True
        n.set(False)
        assert n.get() is False

    def test_label(self):
        assert leaf(label="my-leaf").label == "my-leaf"


# ---------------------------------------------------------------------------
# Group — get() aggregation
# ---------------------------------------------------------------------------


class TestGroupGet:
    def test_all_strategy_true_when_all_enabled(self):
        g = Group(strategy=all)
        g.add(leaf(True)).add(leaf(True))
        assert g.get() is True

    def test_all_strategy_false_when_any_disabled(self):
        g = Group(strategy=all)
        g.add(leaf(True)).add(leaf(False))
        assert g.get() is False

    def test_any_strategy_true_when_one_enabled(self):
        g = Group(strategy=any)
        g.add(leaf(False)).add(leaf(True))
        assert g.get() is True

    def test_any_strategy_false_when_all_disabled(self):
        g = Group(strategy=any)
        g.add(leaf(False)).add(leaf(False))
        assert g.get() is False

    def test_non_voting_children_do_not_affect_get(self):
        g = Group(strategy=all)
        g.add(leaf(True), votes=True)
        g.add(leaf(False), votes=False, propagate=False)
        assert g.get() is True

    def test_empty_group_vacuously_true(self):
        assert Group(strategy=all).get() is True


# ---------------------------------------------------------------------------
# Group — set() propagation
# ---------------------------------------------------------------------------


class TestGroupSet:
    def test_set_propagates_to_voting_and_propagate_true_children(self):
        voting = leaf(True)
        controlled = leaf(True)
        g = Group(strategy=all)
        g.add(voting, votes=True, propagate=True)
        g.add(controlled, votes=False, propagate=True)
        g.set(False)
        assert voting.get() is False
        assert controlled.get() is False

    def test_set_does_not_propagate_to_propagate_false_children(self):
        voting = leaf(True)
        adjustable = leaf(True)
        g = Group(strategy=all)
        g.add(voting, votes=True)
        g.add(adjustable, votes=False, propagate=False)
        g.set(False)
        assert voting.get() is False
        assert adjustable.get() is True

    def test_set_propagates_through_nested_groups(self):
        inner_leaf = leaf(True)
        inner = Group(strategy=all)
        inner.add(inner_leaf)
        outer = Group(strategy=all)
        outer.add(inner)
        outer.set(False)
        assert inner_leaf.get() is False


# ---------------------------------------------------------------------------
# Group — gated_get()
# ---------------------------------------------------------------------------


class TestGroupGatedGet:
    def test_returns_false_when_parent_disabled(self):
        child = leaf(True)
        g = Group(strategy=all)
        g.add(leaf(False))  # forces parent off
        g.add(child)
        assert g.get() is False
        assert g.gated_get(child) is False

    def test_returns_child_state_when_parent_enabled(self):
        child = leaf(False)
        g = Group(strategy=any)
        g.add(leaf(True)).add(child)
        assert g.get() is True
        assert g.gated_get(child) is False


# ---------------------------------------------------------------------------
# Group — at() subsystem creation
# ---------------------------------------------------------------------------


class TestGroupAt:
    def test_at_creates_and_reuses_subgroup(self):
        root = Group("root", strategy=all)
        sub1 = root.at("CRP4")
        sub2 = root.at("CRP4")
        assert isinstance(sub1, Group)
        assert sub1 is sub2

    def test_at_creates_nested_path(self):
        root = Group("root", strategy=all)
        deep = root.at("CRP4", "TPG")
        assert deep.label == "TPG"
        assert root.at("CRP4").at("TPG") is deep

    def test_at_subgroup_participates_in_parent_state(self):
        root = Group("root", strategy=all)
        root.at("CRP4").add(leaf(True))
        assert root.get() is True


# ---------------------------------------------------------------------------
# Group — structural accessors
# ---------------------------------------------------------------------------


class TestGroupStructure:
    def test_children_and_voting_children(self):
        g = Group()
        a, b = leaf(), leaf()
        g.add(a, votes=True).add(b, votes=False)
        assert g.children == [a, b]
        assert g.voting_children == [a]

    def test_iter_yields_node_votes_propagate(self):
        g = Group()
        a, b, c = leaf(), leaf(), leaf()
        g.add(a, votes=True, propagate=True)
        g.add(b, votes=False, propagate=True)
        g.add(c, votes=False, propagate=False)
        assert list(g) == [(a, True, True), (b, False, True), (c, False, False)]
