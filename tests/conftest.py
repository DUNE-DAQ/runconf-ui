"""
Shared fixtures for integration tests that require a live conffwk configuration.

Unit tests (test_adapters, test_nodes, test_traversal) use stubs and mocks
and do not depend on any fixture defined here.
"""

import os
import shutil
from pathlib import Path

import pytest
from daqconf.consolidate import consolidate_db

from runconf_ui.utils import open_configuration
from runconf_ui.utils import init_logger


@pytest.fixture(scope="session")
def session_name():
    return "local-1x1-config"

@pytest.fixture(scope="session")
def config_path() -> Path:
    return Path(
        os.environ.get("DAQSYSTEMTEST_SHARE", "")
        + "/config/daqsystemtest/example-configs.data.xml"
    )


@pytest.fixture(scope="session")
def tmp_config_path(tmp_path_factory):
    folder = tmp_path_factory.mktemp("configs")
    return folder / "local-1x1-config.data.xml"


@pytest.fixture(scope="session")
def consolidated_config(tmp_config_path, session_name, config_path):
    consolidate_db(str(config_path), str(tmp_config_path), session_name)
    return open_configuration(tmp_config_path)


@pytest.fixture(scope="session")
def consolidated_session(consolidated_config, session_name):
    return consolidated_config.get_dal("Session", session_name)


@pytest.fixture(scope="session")
def system_config(tmp_config_path):
    initial = Path(__file__).parent / "test_files" / "dummy.yml"
    dest    = tmp_config_path.parent / "runconf-ui-settings" / "dummy.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(initial, dest)
    return dest

