"""
Unit tests for adapters.py.

These tests use mocks for conffwk objects so they can run without a live
DAQ environment. The mock Session tracks disabled DALs the same way the
real Session does.
"""

from unittest.mock import MagicMock

import pytest

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
def session():
    s = MagicMock()
    s.disabled = []
    return s


@pytest.fixture
def resource_dal(session):
    """A DAL that is a valid Resource subclass."""
    dal = MagicMock()
    dal.className.return_value = "ReadoutApplication"
    return dal


@pytest.fixture
def non_resource_dal():
    """A DAL that is NOT a Resource subclass."""
    dal = MagicMock()
    dal.className.return_value = "SourceIDConf"
    return dal


@pytest.fixture
def configuration(resource_dal, non_resource_dal):
    conf = MagicMock()
    conf.superclasses.side_effect = lambda cls, all=False: (
        ["Resource", "ResourceBase"] if cls == "ReadoutApplication" else []
    )
    return conf


# ---------------------------------------------------------------------------
# DisableComponent§
# ---------------------------------------------------------------------------

class TestDisableComponent:

    def test_rejects_non_resource_dal(self, configuration, session, non_resource_dal):
        with pytest.raises(IncompatibleDalException):
            DisableComponent(configuration, session, non_resource_dal)

    def test_enabled_by_default(self, configuration, session, resource_dal):
        adapter = DisableComponent(configuration, session, resource_dal)
        assert adapter.get() is True

    def test_disabled_when_in_session_disabled(self, configuration, session, resource_dal):
        session.disabled.append(resource_dal)
        adapter = DisableComponent(configuration, session, resource_dal)
        assert adapter.get() is False

    def test_set_false_adds_to_disabled(self, configuration, session, resource_dal):
        adapter = DisableComponent(configuration, session, resource_dal)
        adapter.set(False)
        assert resource_dal in session.disabled
        assert adapter.get() is False

    def test_set_true_removes_from_disabled(self, configuration, session, resource_dal):
        session.disabled.append(resource_dal)
        adapter = DisableComponent(configuration, session, resource_dal)
        adapter.set(True)
        assert resource_dal not in session.disabled
        assert adapter.get() is True

    def test_set_false_idempotent(self, configuration, session, resource_dal):
        session.disabled.append(resource_dal)
        adapter = DisableComponent(configuration, session, resource_dal)
        adapter.set(False)
        assert session.disabled.count(resource_dal) == 1

    def test_set_true_idempotent(self, configuration, session, resource_dal):
        adapter = DisableComponent(configuration, session, resource_dal)
        adapter.set(True)
        assert resource_dal not in session.disabled

    def test_set_calls_update_dal(self, configuration, session, resource_dal):
        adapter = DisableComponent(configuration, session, resource_dal)
        adapter.set(False)
        configuration.update_dal.assert_called()

    def test_dal_enabled(self, configuration, session, resource_dal):
        adapter = DisableComponent(configuration, session, resource_dal)
        assert adapter.dal_enabled() is True
        session.disabled.append(resource_dal)
        assert adapter.dal_enabled() is False


# ---------------------------------------------------------------------------
# DisableAttribute
# ---------------------------------------------------------------------------

class TestDisableAttribute:

    @pytest.fixture
    def dal_with_attr(self, session):
        dal = MagicMock()
        dal.className.return_value = "ReadoutApplication"
        dal.tp_generation_enabled = True
        return dal

    @pytest.fixture
    def adapter(self, configuration, session, dal_with_attr):
        return DisableAttribute(
            configuration, session, dal_with_attr, "tp_generation_enabled"
        )

    def test_rejects_missing_attribute(self, configuration, session, resource_dal):
        del resource_dal.tp_generation_enabled
        resource_dal.__dict__ = {}  # ensure hasattr returns False
        bad_dal = MagicMock(spec=[])  # spec=[] means no attributes
        with pytest.raises(AttributeMissingException):
            DisableAttribute(configuration, session, bad_dal, "tp_generation_enabled")

    def test_enabled_when_attribute_true(self, adapter, dal_with_attr):
        dal_with_attr.tp_generation_enabled = True
        assert adapter.get() is True

    def test_disabled_when_attribute_false(self, adapter, dal_with_attr):
        dal_with_attr.tp_generation_enabled = False
        assert adapter.get() is False

    def test_disabled_when_dal_resource_disabled(self, adapter, session, dal_with_attr):
        dal_with_attr.tp_generation_enabled = True
        session.disabled.append(dal_with_attr)
        assert adapter.get() is False

    def test_set_true(self, configuration, adapter, dal_with_attr):
        dal_with_attr.tp_generation_enabled = False
        adapter.set(True)
        assert dal_with_attr.tp_generation_enabled is True
        configuration.update_dal.assert_called_with(dal_with_attr)

    def test_set_false(self, configuration, adapter, dal_with_attr):
        dal_with_attr.tp_generation_enabled = True
        adapter.set(False)
        assert dal_with_attr.tp_generation_enabled is False

    def test_set_no_op_when_unchanged(self, configuration, adapter, dal_with_attr):
        dal_with_attr.tp_generation_enabled = True
        adapter.set(True)
        configuration.update_dal.assert_not_called()

    def test_custom_enabled_disabled_values(self, configuration, session, dal_with_attr):
        dal_with_attr.mode = "active"
        adapter = DisableAttribute(
            configuration, session, dal_with_attr, "mode",
            enabled_value="active", disabled_value="standby"
        )
        assert adapter.get() is True
        adapter.set(False)
        assert dal_with_attr.mode == "standby"

    def test_dal_enabled(self, adapter, session, dal_with_attr):
        assert adapter.dal_enabled() is True
        session.disabled.append(dal_with_attr)
        assert adapter.dal_enabled() is False


# ---------------------------------------------------------------------------
# AdjustableAttribute
# ---------------------------------------------------------------------------

class TestAdjustableAttribute:

    @pytest.fixture
    def dal_with_rate(self, session):
        dal = MagicMock(spec=["trigger_rate_hz", "className"])
        dal.className.return_value = "RandomTCMakerConf"
        dal.trigger_rate_hz = 1.0
        return dal

    @pytest.fixture
    def adapter(self, configuration, session, dal_with_rate):
        return AdjustableAttribute(
            configuration, session, dal_with_rate, "trigger_rate_hz"
        )

    def test_rejects_missing_attribute(self, configuration, session):
        bad_dal = MagicMock(spec=[])
        with pytest.raises(AttributeMissingException):
            AdjustableAttribute(configuration, session, bad_dal, "trigger_rate_hz")

    def test_get_returns_current_value(self, adapter, dal_with_rate):
        dal_with_rate.trigger_rate_hz = 2.5
        assert adapter.get() == 2.5

    def test_set_updates_value(self, configuration, adapter, dal_with_rate):
        adapter.set(5.0)
        assert dal_with_rate.trigger_rate_hz == 5.0
        configuration.update_dal.assert_called_with(dal_with_rate)

    def test_set_no_op_when_unchanged(self, configuration, adapter, dal_with_rate):
        dal_with_rate.trigger_rate_hz = 1.0
        adapter.set(1.0)
        configuration.update_dal.assert_not_called()

    def test_dal_enabled(self, adapter, session, dal_with_rate):
        assert adapter.dal_enabled() is True
        session.disabled.append(dal_with_rate)
        assert adapter.dal_enabled() is False