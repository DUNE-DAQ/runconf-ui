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
    initialised_ui.set_value('detector__Readout__Readout', True)
    assert initialised_ui.get_value('detector__Readout__Readout')
    assert initialised_ui.get_value('detector__Readout__ru-01')
    assert initialised_ui.get_value('detector__Readout__ru-02')

    
    initialised_ui.toggle('detector__Readout__Readout')
    assert not initialised_ui.get_value('detector__Readout__Readout')
    assert not initialised_ui.get_value('detector__Readout__ru-01')
    assert not initialised_ui.get_value('detector__Readout__ru-02')

    initialised_ui.toggle('detector__Readout__Readout')
    assert initialised_ui.get_value('detector__Readout__Readout')

def test_toggle_subsystems(initialised_ui):
    initialised_ui.set_value('detector__Readout__Readout', True)
    initialised_ui.set_value('detector__Readout__ru-01', True)
    initialised_ui.set_value('detector__Readout__ru-02', True)


    initialised_ui.toggle('detector__Readout__ru-02')
    
    assert not initialised_ui.get_value('detector__Readout__Readout')
    assert initialised_ui.get_value('detector__Readout__ru-01')
    assert initialised_ui.get_value('detector__Readout__ru-02')

    initialised_ui.toggle('detector__Readout__ru-01')
    assert not initialised_ui.get_value('detector__Readout__Readout')
    assert not initialised_ui.get_value('detector__Readout__ru-01')
    assert not initialised_ui.get_value('detector__Readout__ru-02')

    initialised_ui.toggle('detector__Readout__Readout')
    assert not initialised_ui.get_value('detector__Readout__Readout')
    assert not initialised_ui.get_value('detector__Readout__ru-01')
    assert not initialised_ui.get_value('detector__Readout__ru-02')
