import pytest

_READOUT_OPTS = {
                "subsystem_dependent": True,
                "components": [
                    {
                        "id": "ru-segment",
                        "class": "Segment"
                    },
                    {
                        "id": "ru-01",
                        "class": "ReadoutApplication",
                        "system_label": "ru-01",
                        "separate_system": True,
                    },
                    {
                        "id": "ru-02",
                        "class": "ReadoutApplication",
                        "system_label": "ru-02",
                        "separate_system": True,
                    }
                ]
            }

_TPG_OPTS = {
                "subsystem_dependent": False,
                "attributes": [
                    {
                        "id": "tp_generation_enabled",
                        "segments": ["ru-segment"],
                        "class": "ReadoutApplication",
                        "separate_system": True,
                        "system_label": "ru-01"
                    },
                ]
            }


_DISABLE_CONFIG_SKELETON = {
    "Detector":{
        'label': "detector",
        "view_panel": "Detector View",
        "Systems": [
            {"Readout": _READOUT_OPTS},
        ]
    },
    "TPG":{
        'label': "TPG",
        "view_panel": "TPG View",
        "Systems": [
            {"TPG": _TPG_OPTS},
        ]
    }

}

@pytest.fixture(scope="session")

def test_config_read(visibility_config):
    assert visibility_config.config.adjustable_skeleton == {}
    assert visibility_config.config.disableable_skeleton == _DISABLE_CONFIG_SKELETON
    
def test_config_open(loaded_visibility_config):
    assert loaded_visibility_config['adjustable'] == {}
    assert len(loaded_visibility_config['disableable']['Detector']['Systems'][0])==3
    
def test_disable_logic(loaded_visibility_config):
    main_container  = loaded_visibility_config['disableable']['Detector']['Systems'][0][0]
    ru_01_container = loaded_visibility_config['disableable']['Detector']['Systems'][0][1]
    ru_02_container = loaded_visibility_config['disableable']['Detector']['Systems'][0][2]

    print(main_container.contained_operations)

    ru_01_container.set_state(True)
    ru_02_container.set_state(True)
    assert main_container.get_state()
    
    ru_01_container.set_state(False)
    assert main_container.get_state()
    assert ru_02_container.get_state()

    ru_02_container.set_state(False)
    assert not main_container.get_state()

    main_container.set_state(True)
    assert ru_01_container.get_state()
    assert ru_02_container.get_state()

    main_container.set_state(False)
    assert not ru_01_container.get_state()
    assert not ru_02_container.get_state()
