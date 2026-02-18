from pathlib import Path
import pytest
import os

from conffwk import Configuration
from daqconf.consolidate import consolidate_db

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
def consolidated_config(tmp_path_factory, session_name, config_path):
    '''
    Consolidate the config so it only has 
    one session to avoid poorly defined behaviour in future
    '''

    consolidated_config_folder=tmp_path_factory.mktemp("configs")
    consolidated_config = consolidated_config_folder/"local-1x1-config.data.xml"
    consolidate_db(str(config_path), str(consolidated_config), session_name)
    return Configuration("oksconflibs:"+str(consolidated_config))

@pytest.fixture(scope="session")
def consolidated_session(consolidated_config, session_name):
    return consolidated_config.get_dal('Session', session_name)