"""
Integration tests against a live conffwk configuration.

Adapter-level integration (DisableComponent, DisableAttribute, AdjustableAttribute)
is covered adequately by test_adapters.py. These tests focus on:
  - Tree construction and state propagation with real DAL objects.
  - SystemConfigReader end-to-end assembly.
"""

import pytest

from runconf_ui.state_tree import (
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
# Tree integration — real DALs, no YAML
# ---------------------------------------------------------------------------


class TestTreeIntegration:
    """
    Manually builds the TPC tree used in the dummy config and verifies
    that state propagation, controlled objects, and diagnostics work
    against a real conffwk configuration.
    """

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
    def tpc_tree(
        self, consolidated_config, consolidated_session, ru01, ru02, ru_segment
    ):
        """
        TPC (all):
          CRP4 (any): ru-01  (votes=True)
          CRP5 (any): ru-02  (votes=True)
          ru-segment          (votes=False, propagate=True)
        """
        for dal in (ru01, ru02, ru_segment):
            Leaf(DisableComponent(consolidated_config, consolidated_session, dal)).set(
                True
            )

        ru01_leaf = Leaf(
            DisableComponent(consolidated_config, consolidated_session, ru01),
            label="ru-01",
        )
        ru02_leaf = Leaf(
            DisableComponent(consolidated_config, consolidated_session, ru02),
            label="ru-02",
        )
        seg_leaf = Leaf(
            DisableComponent(consolidated_config, consolidated_session, ru_segment),
            label="ru-segment",
        )

        root = Group("TPC", strategy=all)
        root.at("CRP4").add(ru01_leaf)
        root.at("CRP5").add(ru02_leaf)
        root.add(seg_leaf, votes=False, propagate=True)
        return root

    @pytest.fixture(autouse=True)
    def restore(self, tpc_tree):
        yield
        tpc_tree.set(True)

    def test_all_enabled_by_default(self, tpc_tree):
        assert tpc_tree.get() is True

    def test_disabling_one_crp_disables_root(self, tpc_tree):
        tpc_tree.at("CRP4").set(False)
        assert tpc_tree.get() is False

    def test_controlled_object_propagates_with_root(self, tpc_tree):
        tpc_tree.set(False)
        assert build_index(tpc_tree)["ru-segment"].get() is False

    def test_disabled_children_diagnostic(self, tpc_tree):
        tpc_tree.at("CRP4").set(False)
        result = disabled_child_nodes(tpc_tree)
        assert any(c.label == "CRP4" for c in result)

    def test_parent_disabled_propagates_to_non_voting_child(self, tpc_tree):
        tpc_tree.at("CRP4").set(False)
        statuses = {s.node.label: s for s in labelled(tpc_tree) if s.node.label}
        assert statuses["TPC"].state == State.DISABLED
        assert statuses["ru-segment"].state == State.PARENT_DISABLED

    def test_build_index_contains_all_labelled(self, tpc_tree):
        assert set(build_index(tpc_tree).keys()) == {
            "TPC",
            "CRP4",
            "CRP5",
            "ru-01",
            "ru-02",
            "ru-segment",
        }


# ---------------------------------------------------------------------------
# SystemConfigReader integration
# ---------------------------------------------------------------------------


class TestSystemConfigReaderIntegration:
    @pytest.fixture
    def assembled(self, system_config, consolidated_config, session_name):
        reader = SystemConfigReader(system_config)
        return reader.assemble_config(consolidated_config, session_name)

    def test_has_disableable_and_adjustable_groups(self, assembled):
        assert assembled.disableable
        assert assembled.adjustable

    def test_detector_group_structure(self, assembled):
        detector = next(g for g in assembled.disableable if g.id == "Detector")
        assert detector.label == "detector"
        assert detector.view_panel == "Detector View"
        index = build_index(detector.systems[0].root)
        assert "ru-01" in index
        assert "ru-02" in index

    def test_tpg_group_has_readout_subsystem(self, assembled):
        tpg = next(g for g in assembled.disableable if g.id == "TPG")
        index = build_index(tpg.systems[0].root)
        assert "Readout" in index

    def test_adjustable_group_structure(self, assembled):
        group = assembled.adjustable[0]
        assert group.id == "Random Trigger Rates"
        index = build_index(group.systems[0].root)
        assert "random-tc-generator - trigger_rate_hz" in index

    def test_adjustable_nodes_unaffected_by_set(self, assembled):
        group = assembled.adjustable[0]
        root = group.systems[0].root
        index = build_index(root)
        rate_node = index["random-tc-generator - trigger_rate_hz"]
        initial = rate_node.get()
        root.set(False)
        assert rate_node.get() == initial

    def test_disableable_set_changes_state(self, assembled):
        root = (
            next(g for g in assembled.disableable if g.id == "Detector").systems[0].root
        )
        root.set(False)
        assert root.get() is False
        root.set(True)
        assert root.get() is True

    def test_non_existent_objects_produce_no_group(self, assembled):
        assert "NotReal" not in [g.id for g in assembled.disableable]
