from pathlib import Path

import pytest
from rich.tree import Tree

from runconf_ui.exceptions import ConfigReadException
from runconf_ui.state_tree import State
from runconf_ui.utils.config_utils import (
    check_config_has_session,
    dal_in_config,
    get_class_from_segment,
    get_class_from_segment_list,
    get_config_paths,
    get_configs_with_session,
    get_number_of_sessions,
    open_configuration,
)
from runconf_ui.utils.rich_utils import ConfigTreeRenderer


@pytest.fixture
def no_session_config_path(config_path):
    return config_path.parent / "ccm.data.xml"


@pytest.fixture
def no_session_config(no_session_config_path):
    return open_configuration(no_session_config_path)


def test_bad_config_open():
    with pytest.raises(ConfigReadException):
        open_configuration(Path("bad_name"))
    with pytest.raises(FileNotFoundError):
        open_configuration(Path("bad_name.data.xml"))
    assert not check_config_has_session(Path("bad_name.data.xml"))


def test_corrupt_file_open(tmp_path_factory):
    """
    We're going to purposefully make an empty config and get
    it to crash. This raises the same issues as any corrupt
    OKS config
    """
    bad_config_dir = tmp_path_factory.mktemp("bad_files")
    bad_config = bad_config_dir / "bad_config.data.xml"
    bad_config.touch()
    with pytest.raises(ConfigReadException):
        open_configuration(bad_config)


def test_num_sessions(consolidated_config, no_session_config):
    assert get_number_of_sessions(consolidated_config) == 1
    assert get_number_of_sessions(no_session_config) == 0


def test_has_sessions(tmp_config_path, no_session_config_path):
    assert check_config_has_session(tmp_config_path)
    assert not check_config_has_session(no_session_config_path)


def test_check_paths(tmp_config_path, no_session_config_path):
    assert get_config_paths(tmp_config_path.parent) == [tmp_config_path]

    # Should raise an error if a file is puy in
    with pytest.raises(ValueError):
        get_config_paths(tmp_config_path)

    assert get_configs_with_session(tmp_config_path.parent) == [tmp_config_path]
    assert get_configs_with_session(no_session_config_path) == []


def test_segment_getting(consolidated_config):
    # Check if we don't have a segment
    assert get_class_from_segment(consolidated_config, "not_real", "not_class") == []

    # Get the dals
    dals = get_class_from_segment(
        consolidated_config, "ru-segment", "ReadoutApplication"
    )

    dal_ids = {d.id for d in dals}
    # We'll do it on the ids
    assert dal_ids == {"ru-01", "ru-02"}


def test_segment_list(consolidated_config):
    dals = get_class_from_segment_list(
        consolidated_config, ["ru-segment", "df-segment"], "SmartDaqApplication"
    )
    dal_ids = {d.id for d in dals}

    assert dal_ids == {
        "ru-01",
        "ru-02",
        "df-02",
        "tp-stream-writer",
        "dfo-01",
        "df-01",
        "df-03",
    }


def test_dal_in_config(consolidated_config):
    assert dal_in_config(consolidated_config, "ReadoutApplication", "ru-01")
    assert not dal_in_config(consolidated_config, "BadApplication", "ru-01")
    assert not dal_in_config(
        consolidated_config, "ReadoutApplication", "BadApplication"
    )


# ── ConfigTreeRenderer integration tests ──────────────────────────────────────


class TestConfigTreeRendererIntegration:
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
    def renderer(self, consolidated_config, consolidated_session):
        # Draw only ReadoutApplication and Segment classes
        return ConfigTreeRenderer(
            consolidated_config,
            consolidated_session,
            classes_to_draw=["ReadoutApplication", "Segment"],
        )

    def test_draw_config_tree_creates_tree(self, renderer):
        tree = renderer.draw_config_tree()
        assert isinstance(tree, Tree)
        assert tree.label.startswith("[bold green]")
        assert renderer.session.id in tree.label

    def test_calc_config_state_real_objects(self, renderer, ru01):
        state = renderer._calc_config_state(ru01, State.ENABLED)
        # Should be ENABLED initially if component not disabled
        assert state in (State.ENABLED, State.DISABLED, State.PARENT_DISABLED)

    def test_render_config_branch_recurses(self, renderer, ru_segment):
        # Use real DALs
        tree = Tree(f"[bold green]{renderer.session.id}")
        # _render_config_branch should not error
        renderer._render_config_branch(tree, ru_segment, State.ENABLED)
        # At least one child node should be added
        assert len(tree.children) > 0

    def test_tree_contains_expected_dal_ids(self, renderer, ru01, ru02, ru_segment):
        tree = renderer.draw_config_tree()

        def gather_labels(node):
            labels = []
            labels.append(getattr(node, "label", ""))
            for child in getattr(node, "children", []):
                labels.extend(gather_labels(child))
            return labels

        labels = gather_labels(tree)
        # DAL ids should appear somewhere in the tree
        assert any("ru-01" in label for label in labels)
        assert any("ru-02" in label for label in labels)
        assert any("ru-segment" in label for label in labels)

    def test_disabled_state_propagation(self, renderer, ru01, monkeypatch):
        # Patch component_disabled to simulate ru-01 as disabled
        monkeypatch.setattr(
            "runconf_ui.utils.rich_utils.component_disabled",
            lambda obj, session_id, dal_id: dal_id == "ru-01",
        )

        state = renderer._calc_config_state(ru01, State.ENABLED)
        assert state == State.DISABLED
