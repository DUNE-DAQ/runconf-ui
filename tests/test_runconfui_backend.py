"""
Backend integration tests.

Tests the RunconfUIBackend public API (toggle, get_value, set_value,
get_values, save_config) against a real conffwk configuration.
"""

import pytest

from runconf_ui import RunconfContext, RunconfUIBackend


@pytest.fixture(scope="session")
def save_path(tmp_path_factory):
    return tmp_path_factory.mktemp("outputs")


@pytest.fixture(scope="session")
def backend(tmp_config_path, save_path):
    context = RunconfContext(
        apparatus="dummy",
        conf_directory=tmp_config_path.parent,
        use_local=True,
        output_directory=save_path,
    )
    b = RunconfUIBackend(context)
    b.set_daq_version(tmp_config_path.parent)
    b.set_daq_session(tmp_config_path)
    b.open_selected_session()
    return b


# ---------------------------------------------------------------------------
# Toggle / get / set on disableable nodes
# ---------------------------------------------------------------------------

class TestDisableableBackend:

    def test_toggle_top_level_propagates_to_children(self, backend):
        backend.set_value('Detector', 'Readout', True)
        assert backend.get_value('Detector', 'Readout')
        assert backend.get_value('Detector', 'Readout__ru-01')
        assert backend.get_value('Detector', 'Readout__ru-02')

        backend.toggle('Detector', 'Readout')
        assert not backend.get_value('Detector', 'Readout')
        assert not backend.get_value('Detector', 'Readout__ru-01')
        assert not backend.get_value('Detector', 'Readout__ru-02')

        backend.toggle('Detector', 'Readout')  # restore

    def test_toggle_subsystem_updates_parent_state(self, backend):
        backend.set_value('Detector', 'Readout', True)

        # Disabling one subsystem leaves parent enabled (OR semantics for subsystem_dependent)
        backend.toggle('Detector', 'Readout__ru-02')
        assert backend.get_value('Detector', 'Readout')
        assert not backend.get_value('Detector', 'Readout__ru-02')

        # Disabling both subsystems disables parent
        backend.toggle('Detector', 'Readout__ru-01')
        assert not backend.get_value('Detector', 'Readout')

        backend.toggle('Detector', 'Readout')  # restore

    def test_get_values_returns_correct_node_status(self, backend):
        backend.set_value('Detector', 'Readout', True)
        vals = backend.get_values()

        assert vals['Detector']['Readout'].is_enabled
        assert vals['Detector']['Readout__ru-01'].is_enabled
        assert vals['Detector']['Readout__ru-02'].is_enabled

        backend.toggle('Detector', 'Readout__ru-02')
        vals = backend.get_values()
        assert not vals['Detector']['Readout__ru-02'].is_enabled
        assert vals['Detector']['Readout__ru-02'].is_interactive  # still interactive (parent on)

        backend.toggle('Detector', 'Readout__ru-01')
        vals = backend.get_values()
        # Both subsystems off → parent off → children become non-interactive
        assert not vals['Detector']['Readout'].is_enabled
        assert not vals['Detector']['Readout__ru-01'].is_interactive
        assert not vals['Detector']['Readout__ru-02'].is_interactive

        backend.toggle('Detector', 'Readout')  # restore


# ---------------------------------------------------------------------------
# Relationship node
# ---------------------------------------------------------------------------

class TestRelationshipBackend:

    def test_toggle_relationship(self, backend):
        backend.set_value('Trigger', 'RandomTrigger', True)
        assert backend.get_value('Trigger', 'RandomTrigger')

        backend.set_value('Trigger', 'RandomTrigger', False)
        assert not backend.get_value('Trigger', 'RandomTrigger')


# ---------------------------------------------------------------------------
# Adjustable node
# ---------------------------------------------------------------------------

class TestAdjustableBackend:

    def test_set_and_get_adjustable_value(self, backend):
        key = "Random Trigger Rates__random-tc-generator - trigger_rate_hz"
        backend.set_value("Random Trigger Rates", key, 100)
        assert backend.get_value("Random Trigger Rates", key) == 100
