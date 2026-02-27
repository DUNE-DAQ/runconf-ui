import pytest
from runconf_ui import RunconfContext, RunconfUI

@pytest.fixture(scope="session")
def initialised_ui(tmp_config_path):
    context = RunconfContext(
        "dummy",
        tmp_config_path.parent,
        True
    )
    
    ui = RunconfUI(context)
    
    ui.set_daq_version(tmp_config_path.parent)
    ui.select_session(tmp_config_path)

    return ui


def test_enable_top_level(initialised_ui):
    initialised_ui.set_value('Detector', 'Readout', True)
    assert initialised_ui.get_value('Detector', 'Readout')
    assert initialised_ui.get_value('Detector', 'Readout__ru-01')
    assert initialised_ui.get_value('Detector', 'Readout__ru-02')

    
    initialised_ui.toggle('Detector','Readout')
    assert not initialised_ui.get_value('Detector', 'Readout')
    assert not initialised_ui.get_value('Detector', 'Readout__ru-01')
    assert not initialised_ui.get_value('Detector', 'Readout__ru-02')

    initialised_ui.toggle('Detector', 'Readout')
    assert initialised_ui.get_value('Detector', 'Readout')

def test_toggle_subsystems(initialised_ui):
    initialised_ui.set_value('Detector', 'Readout', True)
    initialised_ui.set_value('Detector', 'Readout__ru-01', True)
    initialised_ui.set_value('Detector', 'Readout__ru-02', True)

    initialised_ui.toggle('Detector', 'Readout__ru-02')
    assert initialised_ui.get_value('Detector', 'Readout')
    assert initialised_ui.get_value('Detector', 'Readout__ru-01')
    assert not initialised_ui.get_value('Detector', 'Readout__ru-02')

    initialised_ui.toggle('Detector', 'Readout__ru-01')
    assert not initialised_ui.get_value('Detector', 'Readout')
    assert not initialised_ui.get_value('Detector', 'Readout__ru-01')
    assert not initialised_ui.get_value('Detector', 'Readout__ru-02')

    initialised_ui.toggle('Detector', 'Readout')
    assert initialised_ui.get_value('Detector', 'Readout')
    assert initialised_ui.get_value('Detector', 'Readout__ru-01')
    assert initialised_ui.get_value('Detector', 'Readout__ru-02')


def test_get_values_snapshot(initialised_ui):
    # start with the top-level disabled to have a known baseline
    initialised_ui.set_value('Detector', 'Readout', False)

    # enabling the parent should propagate values to children
    initialised_ui.set_value('Detector', 'Readout', True)
    vals = initialised_ui.get_values()
    assert isinstance(vals, dict)
    assert vals['Detector']['Readout'] == (True, True, True)
    assert vals['Detector']['Readout__ru-01'] == (True, True, True)
    assert vals['Detector']['Readout__ru-02'] == (True, True, True)

    # toggle one child off and verify both raw value and enabled flag
    initialised_ui.toggle('Detector', 'Readout__ru-02')
    vals = initialised_ui.get_values()
    assert vals['Detector']['Readout__ru-01'] == (True, True, True)
    assert vals['Detector']['Readout__ru-02'] == (False, False, True)
    assert vals['Detector']['Readout'] == (True, True, True)


    initialised_ui.toggle('Detector', 'Readout__ru-01')
    vals = initialised_ui.get_values()
    assert vals['Detector']['Readout__ru-01'] == (False, False, False)
    assert vals['Detector']['Readout__ru-02'] == (False, False, False)
    assert vals['Detector']['Readout'] == (False, False, True)

