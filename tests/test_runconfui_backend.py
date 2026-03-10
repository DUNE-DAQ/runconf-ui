import pytest

from runconf_ui import RunconfContext, RunconfUI

'''
TODO: Add tests for the saved file
'''

@pytest.fixture(scope="session")
def save_path(tmp_path_factory):
    return tmp_path_factory.mktemp("outputs")

@pytest.fixture(scope="session")
def initialised_ui(tmp_config_path, save_path):
    context = RunconfContext(
        "dummy",
        tmp_config_path.parent,
        True,
        output_directory=save_path
    )
    
    ui = RunconfUI(context)
    
    ui.set_daq_version(tmp_config_path.parent)
    ui.set_daq_session(tmp_config_path)
    ui.open_selected_session()

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
    print( vals['Detector']['Readout__ru-01'])
    assert isinstance(vals, dict)
    assert vals['Detector']['Readout'].is_enabled
    assert vals['Detector']['Readout'].is_interactive
    assert vals['Detector']['Readout__ru-01'].is_enabled
    assert vals['Detector']['Readout__ru-01'].is_interactive
    assert vals['Detector']['Readout__ru-02'].is_enabled
    assert vals['Detector']['Readout__ru-02'].is_interactive

    # toggle one child off and verify both raw value and enabled flag
    initialised_ui.toggle('Detector', 'Readout__ru-02')
    vals = initialised_ui.get_values()
    assert vals['Detector']['Readout__ru-01'].is_enabled
    assert vals['Detector']['Readout__ru-01'].is_interactive
    assert not vals['Detector']['Readout__ru-02'].is_enabled
    assert vals['Detector']['Readout__ru-02'].is_interactive
    assert vals['Detector']['Readout'].is_enabled
    assert vals['Detector']['Readout'].is_interactive

    initialised_ui.toggle('Detector', 'Readout__ru-01')
    vals = initialised_ui.get_values()
    assert not vals['Detector']['Readout__ru-01'].is_enabled
    assert not vals['Detector']['Readout__ru-01'].is_interactive
    assert not vals['Detector']['Readout__ru-02'].is_enabled
    assert not vals['Detector']['Readout__ru-02'].is_interactive
    assert not vals['Detector']['Readout'].is_enabled
    assert vals['Detector']['Readout'].is_interactive
    
    # Finally we can re-enable the parent to restore the children to their last raw value (False) but enabled state (True)
    initialised_ui.toggle('Detector', 'Readout')
    vals = initialised_ui.get_values()
    assert vals['Detector']['Readout'].is_enabled
    assert vals['Detector']['Readout'].is_interactive
    assert vals['Detector']['Readout__ru-01'].is_enabled
    assert vals['Detector']['Readout__ru-01'].is_interactive
    assert vals['Detector']['Readout__ru-02'].is_enabled
    assert vals['Detector']['Readout__ru-01'].is_interactive

def test_relationship_toggle(initialised_ui):
    initialised_ui.set_value('Trigger', 'RandomTrigger', True)
    assert initialised_ui.get_value('Trigger', 'RandomTrigger')    

    initialised_ui.set_value('Trigger', 'RandomTrigger', False)
    assert not initialised_ui.get_value('Trigger', 'RandomTrigger')    


def test_adjustable_toggle(initialised_ui):
    initialised_ui.set_value("Random Trigger Rates", "Random Trigger Rates__random-tc-generator - trigger_rate_hz", 100)
    assert initialised_ui.get_value("Random Trigger Rates", "Random Trigger Rates__random-tc-generator - trigger_rate_hz") == 100

def test_adjustable_incorrect_type(initialised_ui):
    with pytest.raises(ValueError):
        initialised_ui.set_value("Random Trigger Rates", "Random Trigger Rates__random-tc-generator - trigger_rate_hz", "dummy")

def test_save(initialised_ui, save_path):
    initialised_ui.save_config()
    assert (save_path/"dummy.data.xml").is_file()
    