"""
Unit tests for nodes.py.

Uses simple stub adapters rather than mocks so tests read clearly
without mock call assertions cluttering the logic under test.
"""


from runconf_ui.state_tree import (
    Group,
    Leaf,
)

# ---------------------------------------------------------------------------
# Stub adapter
# ---------------------------------------------------------------------------

class StubAdapter:
    """Minimal in-memory adapter for testing tree logic."""

    def __init__(self, value: bool = True):
        self._value = value
        # Simulate dal_enabled via a simple flag
        self._dal_enabled = True

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def dal_enabled(self):
        return self._dal_enabled


def leaf(value: bool = True, label: str = "") -> Leaf:
    return Leaf(StubAdapter(value), label=label)


# ---------------------------------------------------------------------------
# Leaf
# ---------------------------------------------------------------------------

class TestLeaf:

    def test_get_delegates_to_adapter(self):
        assert leaf(True).get() is True

    def test_set_delegates_to_adapter(self):
        leaf_test = leaf(True)
        leaf_test.set(False)
        assert leaf_test.get() is False

    def test_label(self):
        assert leaf(label="my-leaf").label == "my-leaf"


    def test_dal_enabled_delegates_to_adapter(self):
        adapter = leaf(True)
        assert adapter.adapter.dal_enabled() is True
        adapter.adapter._dal_enabled = False
        assert adapter.adapter.dal_enabled() is False


# ---------------------------------------------------------------------------
# Group — get() aggregation
# ---------------------------------------------------------------------------

class TestGroupGet:

    def test_all_enabled_returns_true(self):
        g = Group(strategy=all)
        g.add(leaf(True)).add(leaf(True))
        assert g.get() is True

    def test_any_disabled_returns_false_for_all_strategy(self):
        g = Group(strategy=all)
        g.add(leaf(True)).add(leaf(False))
        assert g.get() is False

    def test_any_enabled_returns_true_for_any_strategy(self):
        g = Group(strategy=any)
        g.add(leaf(False)).add(leaf(True))
        assert g.get() is True

    def test_all_disabled_returns_false_for_any_strategy(self):
        g = Group(strategy=any)
        g.add(leaf(False)).add(leaf(False))
        assert g.get() is False

    def test_vacuously_true_with_no_voting_children(self):
        g = Group(strategy=all)
        g.add(leaf(False), votes=False, propagate=True)
        assert g.get() is True

    def test_non_voting_children_do_not_affect_get(self):
        g = Group(strategy=all)
        g.add(leaf(True), votes=True)
        g.add(leaf(False), votes=False, propagate=False)
        assert g.get() is True

    def test_empty_group_vacuously_true(self):
        g = Group(strategy=all)
        assert g.get() is True


# ---------------------------------------------------------------------------
# Group — set() propagation
# ---------------------------------------------------------------------------

class TestGroupSet:

    def test_set_propagates_to_voting_children(self):
        a, b = leaf(True), leaf(True)
        g = Group(strategy=all)
        g.add(a).add(b)
        g.set(False)
        assert a.get() is False
        assert b.get() is False

    def test_set_propagates_to_non_voting_propagate_true_children(self):
        a = leaf(True)
        controlled = leaf(True)
        g = Group(strategy=all)
        g.add(a, votes=True)
        g.add(controlled, votes=False, propagate=True)
        g.set(False)
        assert a.get() is False
        assert controlled.get() is False

    def test_set_does_not_propagate_to_propagate_false_children(self):
        a = leaf(True)
        adjustable = leaf(True)
        g = Group(strategy=all)
        g.add(a, votes=True)
        g.add(adjustable, votes=False, propagate=False)
        g.set(False)
        assert a.get() is False
        assert adjustable.get() is True  # untouched

    def test_set_true_restores_children(self):
        a, b = leaf(False), leaf(False)
        g = Group(strategy=all)
        g.add(a).add(b)
        g.set(True)
        assert a.get() is True
        assert b.get() is True

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

    def test_returns_child_state_when_parent_enabled(self):
        child = leaf(True)
        g = Group(strategy=all)
        g.add(child)
        assert g.gated_get(child) is True

    def test_returns_false_when_parent_disabled(self):
        disabled_sibling = leaf(False)
        child = leaf(True)
        g = Group(strategy=all)
        g.add(disabled_sibling)
        g.add(child)
        # Parent is disabled because disabled_sibling is False (AND strategy)
        assert g.get() is False
        assert g.gated_get(child) is False

    def test_returns_child_state_for_any_strategy_with_one_enabled(self):
        enabled = leaf(True)
        disabled = leaf(False)
        g = Group(strategy=any)
        g.add(enabled).add(disabled)
        assert g.get() is True
        assert g.gated_get(disabled) is False  # parent is on, child is off
        assert g.gated_get(enabled) is True


# ---------------------------------------------------------------------------
# Group — at() subsystem creation
# ---------------------------------------------------------------------------

class TestGroupAt:

    def test_at_creates_subgroup(self):
        root = Group("root", strategy=all)
        sub = root.at("CRP4")
        assert isinstance(sub, Group)
        assert sub.label == "CRP4"

    def test_at_returns_existing_subgroup(self):
        root = Group("root", strategy=all)
        sub1 = root.at("CRP4")
        sub2 = root.at("CRP4")
        assert sub1 is sub2

    def test_at_creates_nested_path(self):
        root = Group("root", strategy=all)
        deep = root.at("CRP4", "TPG")
        assert isinstance(deep, Group)
        assert deep.label == "TPG"
        assert root.at("CRP4").at("TPG") is deep

    def test_at_creates_intermediate_groups(self):
        root = Group("root", strategy=all)
        root.at("A", "B", "C")
        assert root.at("A").label == "A"
        assert root.at("A", "B").label == "B"
        assert root.at("A", "B", "C").label == "C"

    def test_at_subgroup_added_as_voting_child(self):
        root = Group("root", strategy=all)
        root.at("CRP4").add(leaf(True))
        assert root.get() is True

    def test_at_returns_self_type_for_chaining(self):
        root = Group("root", strategy=all)
        result = root.at("CRP4").add(leaf(True))
        assert isinstance(result, Group)


# ---------------------------------------------------------------------------
# Group — add() chaining
# ---------------------------------------------------------------------------

class TestGroupAdd:

    def test_add_returns_self_for_chaining(self):
        g = Group()
        a, b = leaf(), leaf()
        result = g.add(a).add(b)
        assert result is g
        assert len(g.children) == 2

    def test_children_property(self):
        g = Group()
        a, b = leaf(), leaf()
        g.add(a).add(b, votes=False, propagate=False)
        assert g.children == [a, b]

    def test_voting_children_property(self):
        g = Group()
        a = leaf()
        b = leaf()
        g.add(a, votes=True).add(b, votes=False)
        assert g.voting_children == [a]

    def test_iter_yields_node_votes_propagate(self):
        g = Group()
        a, b, c = leaf(), leaf(), leaf()
        g.add(a, votes=True,  propagate=True)
        g.add(b, votes=False, propagate=True)
        g.add(c, votes=False, propagate=False)
        items = list(g)
        assert items == [(a, True, True), (b, False, True), (c, False, False)]


# ---------------------------------------------------------------------------
# Nested group integration
# ---------------------------------------------------------------------------

class TestNestedGroups:

    def test_subsystem_disabled_disables_parent(self):
        crp4 = Group("CRP4", strategy=any)
        crp4.add(leaf(False))

        root = Group("TPC", strategy=all)
        root.add(crp4)

        assert root.get() is False

    def test_one_subsystem_off_does_not_disable_or_parent(self):
        crp4 = Group("CRP4", strategy=any)
        crp4.add(leaf(True))

        crp5 = Group("CRP5", strategy=any)
        crp5.add(leaf(False))

        root = Group("TPC", strategy=any)
        root.add(crp4).add(crp5)

        assert root.get() is True

    def test_controlled_object_set_when_parent_set(self):
        controlled = leaf(True)
        voting = leaf(True)

        root = Group("TPC", strategy=all)
        root.add(voting, votes=True,  propagate=True)
        root.add(controlled, votes=False, propagate=True)

        root.set(False)
        assert voting.get() is False
        assert controlled.get() is False

    def test_adjustable_untouched_when_parent_set(self):
        voting = leaf(True)
        adjustable = leaf(True)

        root = Group("TPC", strategy=all)
        root.add(voting, votes=True,  propagate=True)
        root.add(adjustable, votes=False, propagate=False)

        root.set(False)
        assert voting.get() is False
        assert adjustable.get() is True  # untouched