import os
from pathlib import Path

import pytest
from conffwk import Configuration
from daqconf.consolidate import consolidate_db

from runconf_ui.utils import open_configuration

@pytest.fixture(scope="session")
def session_name():
    return "local-1x1-config"

@pytest.fixture(scope="session")
def config_path()->Path:
    return Path(
        os.environ.get("DAQSYSTEMTEST_SHARE", "")
        +"/config/daqsystemtest/example-configs.data.xml"
    )

@pytest.fixture(scope="session")
def tmp_config_path(tmp_path_factory):
    consolidated_config_folder=tmp_path_factory.mktemp("configs")
    consolidated_config_path = consolidated_config_folder/"local-1x1-config.data.xml"
    return consolidated_config_path

@pytest.fixture(scope="session")
def consolidated_config(tmp_config_path, session_name, config_path):
    '''
    Consolidate the config so it only has 
    one session to avoid poorly defined behaviour in future
    '''
    consolidate_db(str(config_path), str(tmp_config_path), session_name)
    return open_configuration(tmp_config_path)

@pytest.fixture(scope="session")
def consolidated_session(consolidated_config, session_name):
    return consolidated_config.get_dal('Session', session_name)

@pytest.fixture(scope="session")
def runconf_ui_config(tmp_config_path):
    config_path = tmp_config_path.parent/"runconf-ui-settings"/"dummy.yml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.touch()
    return config_path