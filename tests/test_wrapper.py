import pytest

from runconf_ui.exceptions import RunConfToolsRepoException
from runconf_ui.runconf_backend_wrapper import RunconBackendWrapper


def test_wrapper_load(tmp_config_path):
        dummy_wrapper = RunconBackendWrapper("dummy", tmp_config_path.parent, True)
        
        dummy_wrapper.set_daq_version(None)
        assert dummy_wrapper.configuration is None
        assert dummy_wrapper.system_config_reader is None
        assert dummy_wrapper.state_operations_tree is None
        
        with pytest.raises(RunConfToolsRepoException):
            dummy_wrapper.select_config(tmp_config_path)
 
        
        # We handle this in other tests, but here is the check for completeness
        dummy_wrapper.set_daq_version(tmp_config_path.parent)
        dummy_wrapper.select_config(tmp_config_path)
        assert dummy_wrapper.configuration is not None
        assert dummy_wrapper.system_config_reader is not None
        assert dummy_wrapper.state_operations_tree is not None
        
def test_bad_remote(tmp_config_path):
    with pytest.raises(RunConfToolsRepoException):
        RunconBackendWrapper("dummy", tmp_config_path.parent, False)