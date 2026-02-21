'''
A set of tests to check the system config is working as intended
'''
import pytest

# Easiest to do this from loading a config
from runconf_ui.system_configuration import SystemConfigReader
from runconf_ui.system_configuration.system_builders import create_system_builder


@pytest.fixture
def assembled_config(system_config, consolidated_config, session_name):
    # No real tests needed on the reader since it's just loading YAML 
    reader = SystemConfigReader(system_config)

    return reader.assemble_config(consolidated_config, session_name)

def test_incorrect_builder(consolidated_config, consolidated_session):
    with pytest.raises(ValueError):
        create_system_builder("dummy", consolidated_config, consolidated_session)

def test_disable_system(assembled_config):
    disabled_elements = assembled_config.get('disableable')
    assert disabled_elements is not None
    
    # Now we prope this has been made correctly!
    assert len(disabled_elements) == 2
    
    # Now we get the 0th element (the readout)
    detector_element = disabled_elements[0]
    assert detector_element['id'] == "Detector"
    assert detector_element['label'] == "detector"
    assert detector_element['view_panel'] == "Detector View"
    
    detector_systems = detector_element['systems'][0]
    assert not detector_systems['display_full_system']
    
    system_container = detector_systems['system']
    
    assert set(system_container.get_nested_registry()) == {"ru-01", "ru-02"}
    assert set(d.dal.id for d in system_container.controlled_objects) == {'ru-segment'}
    assert set(system_container.subsystem_registry) == {"ru-01", "ru-02"}
    assert set(system_container.get_nested_registry().keys()) == {"ru-01", "ru-02"}
    
    # Now we test the adjustable attribute
    tpg_element = disabled_elements[1]
    tpg_container = tpg_element['systems'][0]['system']
    
    # Want to access the containers 
    tpg_containers = tpg_container.get_nested_registry()["readout"].state_operations[0].state_operations
    assert {t.dal.id for t in tpg_containers} == {"ru-01", "ru-02"}
    
    
def test_adjust_system(assembled_config):
    adjustable_elements = assembled_config.get('adjustable')
    
    assert adjustable_elements is not None
    
    assert len(adjustable_elements) == 1
    
    adjustable_element = adjustable_elements[0]
    assert adjustable_element['id'] == 'Random Trigger Rates'
    
    system_container = adjustable_element['systems'][0]['system']
    assert set(system_container.get_nested_registry().keys()) == {'random-tc-generator'}
