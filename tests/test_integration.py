"""
Integration tests against a live conffwk configuration.

These tests verify that the full stack — adapters reading/writing real DALs,
nodes aggregating real state, traversal computing correct NodeStatus values —
works correctly end-to-end.

All tests restore state after themselves so they can run in any order.
"""

import pytest

from runconf_ui.exceptions import AttributeMissingException, IncompatibleDalException
from runconf_ui.state_tree import (
    AdjustableAttribute,
    DisableAttribute,
    DisableComponent,
    Group,
    Leaf,
    State,
    build_index,
    disabled_child_nodes,
    labelled,
)
from runconf_ui.system_configuration import SystemConfigReader

# ---------------------------------------------------------------------------
# Adapter integration
# ---------------------------------------------------------------------------

class TestDisableComponentIntegration:

    @pytest.fixture
    def ru01(self, consolidated_config):
        return consolidated_config.get_dal("ReadoutApplication", "ru-01")

    @pytest.fixture
    def adapter(self, consolidated_config, consolidated_session, ru01):
        return DisableComponent(consolidated_config, consolidated_session, ru01)

    def test_enabled_by_default(self, adapter):
        assert adapter.get() is True

    def test_disable_and_restore(self, adapter):
        adapter.set(False)
        assert adapter.get() is False
        adapter.set(True)
        assert adapter.get() is True

    def test_rejects_non_resource(self, consolidated_config, consolidated_session):
        dal = consolidated_config.get_dal("SourceIDConf", "tp-srcid-1001")
        with pytest.raises(IncompatibleDalException):
            DisableComponent(consolidated_config, consolidated_session, dal)

    def test_dal_enabled_reflects_session_state(self, adapter, consolidated_session, ru01):
        assert adapter.dal_enabled() is True
        adapter.set(False)
        assert adapter.dal_enabled() is False
        adapter.set(True)


class TestDisableAttributeIntegration:

    @pytest.fixture
    def ru01(self, consolidated_config):
        return consolidated_config.get_dal("ReadoutApplication", "ru-01")

    @pytest.fixture
    def adapter(self, consolidated_config, consolidated_session, ru01):
        return DisableAttribute(
            consolidated_config, consolidated_session, ru01, "tp_generation_enabled"
        )

    def test_get_reflects_attribute(self, adapter, ru01):
        initial = adapter.get()
        assert isinstance(initial, bool)

    def test_set_and_restore(self, adapter):
        initial = adapter.get()
        adapter.set(not initial)
        assert adapter.get() is not initial
        adapter.set(initial)
        assert adapter.get() is initial

    def test_disabled_when_dal_resource_disabled(
        self, consolidated_config, consolidated_session, ru01
    ):
        attr_adapter = DisableAttribute(
            consolidated_config, consolidated_session, ru01, "tp_generation_enabled"
        )
        res_adapter = DisableComponent(
            consolidated_config, consolidated_session, ru01
        )
        attr_adapter.set(True)
        res_adapter.set(False)
        assert attr_adapter.get() is False
        res_adapter.set(True)

    def test_rejects_missing_attribute(self, consolidated_config, consolidated_session, ru01):
        with pytest.raises(AttributeMissingException):
            DisableAttribute(
                consolidated_config, consolidated_session, ru01, "not_a_real_attr"
            )


class TestAdjustableAttributeIntegration:

    @pytest.fixture
    def dal(self, consolidated_config):
        return consolidated_config.get_dal("SourceIDConf", "tp-srcid-1001")

    @pytest.fixture
    def adapter(self, consolidated_config, consolidated_session, dal):
        return AdjustableAttribute(
            consolidated_config, consolidated_session, dal, "sid"
        )

    def test_get_returns_current_value(self, adapter):
        value = adapter.get()
        assert value is not None

    def test_set_and_restore(self, adapter):
        initial = adapter.get()
        adapter.set(9999)
        assert adapter.get() == 9999
        adapter.set(initial)
        assert adapter.get() == initial

# ---------------------------------------------------------------------------
# Tree integration
# ---------------------------------------------------------------------------

class TestTreeIntegration:

    @pytest.fixture
    def ru01(self, consolidated_config):
        return consolidated_config.get_dal("ReadoutApplication", "ru-01")

    @pytest.fixture
    def ru02(self, consolidated_config):
        return consolidated_config.get_dal("ReadoutApplication", "ru-02")

    @pytest.fixture
    def ru_segment(self, consolidated_config):
        return consolidated_config.get_dal("Segment", "ru-segment")

    @pytest.fixture
    def tpc_tree(self, consolidated_config, consolidated_session, ru01, ru02, ru_segment):
        """
        TPC:
          CRP4 (any):
            ru-01  (votes=True)
          CRP5 (any):
            ru-02  (votes=True)
          ru-segment  (votes=False, propagate=True) — controlled object
        """
        ru01_leaf = Leaf(
            DisableComponent(consolidated_config, consolidated_session, ru01),
            label="ru-01",
        )
        ru01_leaf.set(True)
        ru02_leaf = Leaf(
            DisableComponent(consolidated_config, consolidated_session, ru02),
            label="ru-02",
        )
        ru02_leaf.set(True)
        
        seg_leaf = Leaf(
            DisableComponent(consolidated_config, consolidated_session, ru_segment),
            label="ru-segment",
        )
        seg_leaf.set(True)

        root = Group("TPC", strategy=all)
        root.at("CRP4").add(ru01_leaf)
        root.at("CRP5").add(ru02_leaf)
        root.add(seg_leaf, votes=False, propagate=True)
        return root

    def test_all_enabled_by_default(self, tpc_tree):        
        assert tpc_tree.get() is True

    def test_disable_one_crp_disables_root(self, tpc_tree):
        crp4 = tpc_tree.at("CRP4")
        crp4.set(False)
        assert tpc_tree.get() is False
        crp4.set(True)

    def test_controlled_object_set_with_root(self, tpc_tree, consolidated_config, ru_segment):
        tpc_tree.set(False)
        # ru-segment should be disabled (propagate=True)
        index = build_index(tpc_tree)
        assert index["ru-segment"].get() is False
        tpc_tree.set(True)

    def test_disabled_children_diagnostic(self, tpc_tree):
        tpc_tree.at("CRP4").set(False)
        result = disabled_child_nodes(tpc_tree)
        assert any(c.label == "CRP4" for c in result)
        tpc_tree.at("CRP4").set(True)

    def test_parent_disabled_state_propagates_to_labelled(self, tpc_tree):
        tpc_tree.at("CRP4").set(False)

        statuses = {s.node.label: s for s in labelled(tpc_tree) if s.node.label}
        # ru-segment is non-voting; CRP4 going off disables root
        assert statuses["TPC"].state == State.DISABLED
        assert statuses["ru-segment"].state == State.PARENT_DISABLED

        tpc_tree.at("CRP4").set(True)

    def test_build_index_contains_all_labelled(self, tpc_tree):
        index = build_index(tpc_tree)
        assert set(index.keys()) == {"TPC", "CRP4", "CRP5", "ru-01", "ru-02", "ru-segment"}


# ---------------------------------------------------------------------------
# SystemConfigReader integration
# ---------------------------------------------------------------------------

class TestSystemConfigReaderIntegration:

    @pytest.fixture
    def assembled(self, system_config, consolidated_config, session_name):
        reader = SystemConfigReader(system_config)
        return reader.assemble_config(consolidated_config, session_name)

    def test_assembled_config_has_disableable_and_adjustable(self, assembled):
        assert assembled.disableable is not None
        assert assembled.adjustable is not None

    def test_detector_group_structure(self, assembled):
        detector = next(g for g in assembled.disableable if g.id == "Detector")
        assert detector.label == "detector"
        assert detector.view_panel == "Detector View"

        system = detector.systems[0]
        index = build_index(system.root)
        assert "ru-01" in index
        assert "ru-02" in index

    def test_tpg_group_structure(self, assembled):
        tpg = next(g for g in assembled.disableable if g.id == "TPG")
        system = tpg.systems[0]
        index = build_index(system.root)
        assert "readout" in index

    def test_adjustable_group_structure(self, assembled):
        assert len(assembled.adjustable) == 1
        group = assembled.adjustable[0]
        assert group.id == "Random Trigger Rates"
        index = build_index(group.systems[0].root)
        assert "random-tc-generator" in index

    def test_adjustable_node_not_affected_by_set(self, assembled):
        group = assembled.adjustable[0]
        root  = group.systems[0].root
        index = build_index(root)
        rate_node = index["random-tc-generator"]
        initial = rate_node.get()

        # set() on root must not touch adjustable nodes
        root.set(False)
        assert rate_node.get() == initial

    def test_disableable_set_changes_config_state(self, assembled):
        detector = next(g for g in assembled.disableable if g.id == "Detector")
        root = detector.systems[0].root
        _ = build_index(root)

        root.set(False)
        assert root.get() is False

        root.set(True)
        assert root.get() is True
        
    def test_non_existent_object(self, assembled):
        '''We define a system in the config, we need to check if it shows up!'''
        g_ids = [g.id for g in assembled.disableable]
        assert "NotReal" not in g_ids
