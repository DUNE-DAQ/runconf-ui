"""
Unit tests for adapters.py.

Uses a live conffwk configuration (via conftest fixtures) since the adapters
are thin wrappers around conffwk calls. State is always restored after each
test via yield fixtures so tests are order-independent.
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
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def non_resource_dal(consolidated_config):
    return consolidated_config.get_dal("SourceIDConf", "tp-srcid-1001")


@pytest.fixture
def resource_dal(consolidated_config):
    return consolidated_config.get_dal("ReadoutApplication", "ru-01")


@pytest.fixture(autouse=True)
def restore_resource_dal(consolidated_config, consolidated_session, resource_dal):
    """Ensure ru-01 is always re-enabled after each test."""
    yield
    enable_component(consolidated_config._obj, consolidated_session.id, resource_dal.id)


# ---------------------------------------------------------------------------
# DisableComponent
# ---------------------------------------------------------------------------


class TestDisableComponent:
    def test_rejects_non_resource_dal(
        self, consolidated_config, consolidated_session, non_resource_dal
    ):
        with pytest.raises(IncompatibleDalException):
            DisableComponent(
                consolidated_config, consolidated_session, non_resource_dal
            )

    def test_enabled_by_default(
        self, consolidated_config, consolidated_session, resource_dal
    ):
        adapter = DisableComponent(
            consolidated_config, consolidated_session, resource_dal
        )
        assert adapter.get() is True

    def test_set_false_disables(
        self, consolidated_config, consolidated_session, resource_dal
    ):
        adapter = DisableComponent(
            consolidated_config, consolidated_session, resource_dal
        )
        adapter.set(False)
        assert adapter.get() is False
        assert component_disabled(
            consolidated_config._obj, consolidated_session.id, resource_dal.id
        )

    def test_set_true_enables(
        self, consolidated_config, consolidated_session, resource_dal
    ):
        disable_component(
            consolidated_config._obj, consolidated_session.id, resource_dal.id
        )
        adapter = DisableComponent(
            consolidated_config, consolidated_session, resource_dal
        )
        adapter.set(True)
        assert adapter.get() is True
        assert not component_disabled(
            consolidated_config._obj, consolidated_session.id, resource_dal.id
        )


# ---------------------------------------------------------------------------
# DisableAttribute
# ---------------------------------------------------------------------------


class TestDisableAttribute:
    @pytest.fixture
    def adapter(self, consolidated_config, consolidated_session, resource_dal):
        return DisableAttribute(
            consolidated_config,
            consolidated_session,
            resource_dal,
            "tp_generation_enabled",
        )

    def test_rejects_missing_attribute(
        self, consolidated_config, consolidated_session, non_resource_dal
    ):
        with pytest.raises(AttributeMissingException):
            DisableAttribute(
                consolidated_config,
                consolidated_session,
                non_resource_dal,
                "tp_generation_enabled",
            )

    def test_get_reflects_attribute_value(self, adapter, resource_dal):
        resource_dal.tp_generation_enabled = True
        assert adapter.get() is True
        resource_dal.tp_generation_enabled = False
        assert adapter.get() is False

    def test_disabled_when_dal_resource_disabled(
        self, adapter, consolidated_config, consolidated_session, resource_dal
    ):
        resource_dal.tp_generation_enabled = True
        disable_component(
            consolidated_config._obj, consolidated_session.id, resource_dal.id
        )
        assert adapter.get() is False

    def test_set_updates_attribute(self, adapter, resource_dal):
        adapter.set(True)
        assert resource_dal.tp_generation_enabled is True
        adapter.set(False)
        assert resource_dal.tp_generation_enabled is False

    def test_custom_enabled_disabled_values(
        self, consolidated_config, consolidated_session, non_resource_dal
    ):
        non_resource_dal.sid = 1001
        adapter = DisableAttribute(
            consolidated_config,
            consolidated_session,
            non_resource_dal,
            "sid",
            enabled_value=1001,
            disabled_value=1002,
        )
        assert adapter.get() is True
        adapter.set(False)
        assert non_resource_dal.sid == 1002


# ---------------------------------------------------------------------------
# AdjustableAttribute
# ---------------------------------------------------------------------------


class TestAdjustableAttribute:
    @pytest.fixture
    def dal(self, consolidated_config):
        dal = consolidated_config.get_dal("RandomTCMakerConf", "random-tc-generator")
        dal.trigger_rate_hz = 1.0
        return dal

    @pytest.fixture
    def adapter(self, consolidated_config, consolidated_session, dal):
        return AdjustableAttribute(
            consolidated_config, consolidated_session, dal, "trigger_rate_hz"
        )

    def test_rejects_missing_attribute(
        self, consolidated_config, consolidated_session, non_resource_dal
    ):
        with pytest.raises(AttributeMissingException):
            AdjustableAttribute(
                consolidated_config,
                consolidated_session,
                non_resource_dal,
                "trigger_rate_hz",
            )

    def test_get_and_set(self, adapter, dal):
        adapter.set(5.0)
        assert adapter.get() == 5.0
        adapter.set(1.0)
        assert adapter.get() == 1.0
