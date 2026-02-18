import pytest
from pathlib import Path

from runconf_ui.utils.config_utils import (open_configuration,
                                           get_number_of_sessions,
                                           check_config_has_session,
                                           get_config_paths,
                                           get_configs_with_session)

from runconf_ui.exceptions import ConfigReadException

'''
TODO: Test opening corrupted file
'''

@pytest.fixture
def no_session_config_path(config_path):
    return config_path.parent/"ccm.data.xml"

@pytest.fixture
def no_session_config(no_session_config_path):
    return open_configuration(no_session_config_path)
    

def test_bad_config_open():
    with pytest.raises(ConfigReadException):
        open_configuration(Path("bad_name"))
    with pytest.raises(FileNotFoundError):
        open_configuration(Path("bad_name.data.xml"))

    assert check_config_has_session(Path("bad_name.data.xml")) == False

        
def test_num_sessions(consolidated_config, no_session_config):
    assert get_number_of_sessions(consolidated_config) == 1
    assert get_number_of_sessions(no_session_config) == 0
    
def test_has_sessions(tmp_config_path, no_session_config_path):
    assert check_config_has_session(tmp_config_path) == True
    assert check_config_has_session(no_session_config_path) == False
    
def test_check_paths(tmp_config_path, no_session_config_path):
    assert get_config_paths(tmp_config_path.parent) == [tmp_config_path]

    # Should raise an error if a file is puy in
    with pytest.raises(ValueError):
        get_config_paths(tmp_config_path)
    
    
    assert get_configs_with_session(tmp_config_path.parent) == [tmp_config_path]
    assert get_configs_with_session(no_session_config_path) == []