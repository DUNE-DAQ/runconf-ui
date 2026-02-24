"""
Unit tests for adapters.py.

These tests use mocks for conffwk objects so they can run without a live
DAQ environment. The mock consolidated_session tracks disabled DALs the same way the
real consolidated_session does.
"""


import pytest
from confmodel_dal import component_disabled, disable_component, enable_component

from runconf_ui.exceptions import AttributeMissingException, IncompatibleDalException
from runconf_ui.state_tree import (
    AdjustableAttribute,
    DisableAttribute,
    DisableComponent,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def non_resource_dal(consolidated_config):
    return consolidated_config.get_dal("SourceIDConf", "tp-srcid-1001")

@pytest.fixture
def resource_dal(consolidated_config):
    return consolidated_config.get_dal("ReadoutApplication", "ru-01")

# ---------------------------------------------------------------------------
# DisableComponent§
# ---------------------------------------------------------------------------

class TestDisableComponent:

    def test_rejects_non_resource_dal(self, consolidated_config, consolidated_session, non_resource_dal):
        with pytest.raises(IncompatibleDalException):
            DisableComponent(consolidated_config, consolidated_session, non_resource_dal)

    def test_enabled_by_default(self, consolidated_config, consolidated_session, resource_dal):
        enable_component(consolidated_config._obj, consolidated_session.id, resource_dal.id)
        adapter = DisableComponent(consolidated_config, consolidated_session, resource_dal)
        assert adapter.get() is True

    def test_disabled_when_in_consolidated_session_disabled(self, consolidated_config, consolidated_session, resource_dal):
        disable_component(consolidated_config._obj, consolidated_session.id, resource_dal.id)
        adapter = DisableComponent(consolidated_config, consolidated_session, resource_dal)
        assert adapter.get() is False
        adapter.set(True)

    def test_set_false_adds_to_disabled(self, consolidated_config, consolidated_session, resource_dal):
        adapter = DisableComponent(consolidated_config, consolidated_session, resource_dal)
        adapter.set(False)
        assert component_disabled(consolidated_config._obj, consolidated_session.id, resource_dal.id)
        assert adapter.get() is False
        adapter.set(True)

    def test_set_true_removes_from_disabled(self, consolidated_config, consolidated_session, resource_dal):
        disable_component(consolidated_config._obj, consolidated_session.id, resource_dal.id)
        adapter = DisableComponent(consolidated_config, consolidated_session, resource_dal)
        adapter.set(True)
        assert not component_disabled(consolidated_config._obj, consolidated_session.id, resource_dal.id)
        assert adapter.get() is True

    def test_set_true_idempotent(self, consolidated_config, consolidated_session, resource_dal):
        adapter = DisableComponent(consolidated_config, consolidated_session, resource_dal)
        adapter.set(True)
        assert resource_dal not in consolidated_session.disabled

# ---------------------------------------------------------------------------
# DisableAttribute
# ---------------------------------------------------------------------------

class TestDisableAttribute:

    # @pytest.fixture
    # def dal_with_attr(self, consolidated_session):
    #     dal = MagicMock()
    #     dal.className.return_value = "ReadoutApplication"
    #     dal.tp_generation_enabled = True
    #     return dal

    @pytest.fixture
    def adapter(self, consolidated_config, consolidated_session, resource_dal):
        return DisableAttribute(
            consolidated_config, consolidated_session, resource_dal, "tp_generation_enabled"
        )

    def test_rejects_missing_attribute(self, consolidated_config, consolidated_session, non_resource_dal):
        with pytest.raises(AttributeMissingException):
            DisableAttribute(consolidated_config, consolidated_session, non_resource_dal, "tp_generation_enabled")

    def test_enabled_when_attribute_true(self, adapter, resource_dal):
        resource_dal.tp_generation_enabled = True
        assert adapter.get() is True

    def test_disabled_when_attribute_false(self, adapter, resource_dal):
        resource_dal.tp_generation_enabled = False
        assert adapter.get() is False

    def test_disabled_when_dal_resource_disabled(self, adapter, consolidated_config, consolidated_session, resource_dal):
        resource_dal.tp_generation_enabled = True
        disable_component(consolidated_config._obj, consolidated_session.id, resource_dal.id)
        assert adapter.get() is False

    def test_set_true(self, adapter, resource_dal):
        resource_dal.tp_generation_enabled = False
        adapter.set(True)
        assert resource_dal.tp_generation_enabled is True

    def test_set_false(self, adapter, resource_dal):
        resource_dal.tp_generation_enabled = True
        adapter.set(False)
        assert resource_dal.tp_generation_enabled is False

    def test_custom_enabled_disabled_values(self, consolidated_config, consolidated_session, non_resource_dal):
        non_resource_dal.sid = 1001
        adapter = DisableAttribute(
            consolidated_config, consolidated_session, non_resource_dal, "sid",
            enabled_value=1001, disabled_value=1002
        )
        assert adapter.get() is True
        adapter.set(False)
        assert non_resource_dal.sid == 1002

    def test_dal_enabled(self, adapter, consolidated_config, consolidated_session, resource_dal):
        enable_component(consolidated_config._obj, consolidated_session.id, resource_dal.id)
        assert adapter.dal_enabled() is True
        disable_component(consolidated_config._obj, consolidated_session.id, resource_dal.id)
        assert adapter.dal_enabled() is False
        enable_component(consolidated_config._obj, consolidated_session.id, resource_dal.id)


# ---------------------------------------------------------------------------
# AdjustableAttribute
# ---------------------------------------------------------------------------

class TestAdjustableAttribute:

    @pytest.fixture
    def dal_with_rate(self, consolidated_config):
        dal = consolidated_config.get_dal("RandomTCMakerConf","random-tc-generator")
        dal.trigger_rate_hz=1.0
        return dal

    @pytest.fixture
    def adapter(self, consolidated_config, consolidated_session, dal_with_rate):
        return AdjustableAttribute(
            consolidated_config, consolidated_session, dal_with_rate, "trigger_rate_hz"
        )

    def test_rejects_missing_attribute(self, consolidated_config, consolidated_session, non_resource_dal):
        with pytest.raises(AttributeMissingException):
            AdjustableAttribute(consolidated_config, consolidated_session, non_resource_dal, "trigger_rate_hz")

    def test_get_returns_current_value(self, adapter, dal_with_rate):
        dal_with_rate.trigger_rate_hz = 2.5
        assert adapter.get() == 2.5

    def test_set_updates_value(self, adapter, dal_with_rate):
        adapter.set(5.0)
        assert dal_with_rate.trigger_rate_hz == 5.0
        adapter.set(1.0)
        assert dal_with_rate.trigger_rate_hz == 1.0