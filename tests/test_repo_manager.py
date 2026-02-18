from pathlib import Path

import pytest

from runconf_ui.exceptions import DaqVersionException, MissingRunconfUIConfigException
from runconf_ui.repo_manager import LocalRepoManager


@pytest.fixture(scope="session")
def local_repo_manager(tmp_config_path, consolidated_config):
    # Bit hacky, ensure's we've made this before proceeding
    assert consolidated_config is not None
    
    return LocalRepoManager("dummy", 
                                    conf_directory = tmp_config_path.parent)
    
def test_daq_versions(tmp_config_path, local_repo_manager):
    
        with pytest.raises(DaqVersionException):
            local_repo_manager.set_daq_version(Path("dummy"))        
        assert local_repo_manager.get_available_daq_versions() == [tmp_config_path.parent]
        assert local_repo_manager.get_daq_sessions() == [tmp_config_path]
        assert local_repo_manager.select_config(tmp_config_path) == tmp_config_path
        assert local_repo_manager.select_config(tmp_config_path.name) == tmp_config_path
        with pytest.raises(DaqVersionException):
            local_repo_manager.select_config(Path("not a real config"))

def test_find_config(local_repo_manager, visibility_config_path):
    local_repo_manager.apparatus = "other"
    
    with pytest.raises(MissingRunconfUIConfigException):
        local_repo_manager.get_runconf_ui_config_path()

    local_repo_manager.apparatus = "dummy"
    
    assert local_repo_manager.get_runconf_ui_config_path() == visibility_config_path
    