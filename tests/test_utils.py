from pathlib import Path

import pytest

from runconf_ui.exceptions import ConfigReadException
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
    assert not check_config_has_session(Path("bad_name.data.xml"))

def test_corrupt_file_open(tmp_path_factory):
    '''
    We're going to purposefully make an empty config and get
    it to crash. This raises the same issues as any corrupt
    OKS config
    '''
    bad_config_dir = tmp_path_factory.mktemp("bad_files")
    bad_config = bad_config_dir/"bad_config.data.xml"
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
    with pytest.raises(ConfigReadException):
        get_class_from_segment(consolidated_config, "not_real", "not_class") == []
    
    # Get the dals
    dals = get_class_from_segment(consolidated_config, "ru-segment", "ReadoutApplication")
    
    dal_ids = {d.id for d in dals}
    # We'll do it on the ids
    assert dal_ids == {'ru-01', 'ru-02'}
    
def test_segment_list(consolidated_config):
    dals = get_class_from_segment_list(consolidated_config, ['ru-segment', 'df-segment'], 'SmartDaqApplication')
    dal_ids = {d.id for d in dals}
    
    assert dal_ids == {'ru-01', 'ru-02', 'df-02', 'tp-stream-writer', 'dfo-01', 'df-01', 'df-03'}
    
def test_dal_in_config(consolidated_config):
    assert dal_in_config(consolidated_config, 'ReadoutApplication', 'ru-01')
    assert not dal_in_config(consolidated_config, 'BadApplication', 'ru-01')
    assert not dal_in_config(consolidated_config, 'ReadoutApplication', 'BadApplication')