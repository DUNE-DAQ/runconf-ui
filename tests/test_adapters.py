"""
Unit tests for adapters.py.

Uses a live conffwk configuration (via conftest fixtures) since the adapters
are thin wrappers around conffwk calls. State is always restored after each
test via yield fixtures so tests are order-independent.
"""

import pytest
from confmodel_dal import entity_excluded, exclude_entity, include_entity

from runconf_ui.exceptions import AttributeMissingException, IncompatibleDalException
from runconf_ui.state_tree import (
    AttributeAdapter,
    AdjustableAttributeAdapter,
    ExcludableEntityAdapter,
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
    """Ensure ru-01 is always re-included after each test."""
    yield
    include_entity(consolidated_config._obj, consolidated_session.id, resource_dal.id)


# ---------------------------------------------------------------------------
# excludeComponent
# ---------------------------------------------------------------------------


class TestexcludeComponent:
    def test_rejects_non_resource_dal(
        self, consolidated_config, consolidated_session, non_resource_dal
    ):
        with pytest.raises(IncompatibleDalException):
            ExcludableEntityAdapter(
                consolidated_config, consolidated_session, non_resource_dal
            )

    def test_included_by_default(
        self, consolidated_config, consolidated_session, resource_dal
    ):
        adapter = ExcludableEntityAdapter(
            consolidated_config, consolidated_session, resource_dal
        )
        assert adapter.get() is True

    def test_set_false_excludes(
        self, consolidated_config, consolidated_session, resource_dal
    ):
        adapter = ExcludableEntityAdapter(
            consolidated_config, consolidated_session, resource_dal
        )
        adapter.set(False)
        assert adapter.get() is False
        assert entity_excluded(
            consolidated_config._obj, consolidated_session.id, resource_dal.id
        )

    def test_set_true_includes(
        self, consolidated_config, consolidated_session, resource_dal
    ):
        exclude_entity(
            consolidated_config._obj, consolidated_session.id, resource_dal.id
        )
        adapter = ExcludableEntityAdapter(
            consolidated_config, consolidated_session, resource_dal
        )
        adapter.set(True)
        assert adapter.get() is True
        assert not entity_excluded(
            consolidated_config._obj, consolidated_session.id, resource_dal.id
        )


# ---------------------------------------------------------------------------
# excludeAttribute
# ---------------------------------------------------------------------------


class TestexcludeAttribute:
    @pytest.fixture
    def adapter(self, consolidated_config, consolidated_session, resource_dal):
        return AttributeAdapter(
            consolidated_config,
            consolidated_session,
            resource_dal,
            "tp_generation_enabled",
        )

    def test_rejects_missing_attribute(
        self, consolidated_config, consolidated_session, non_resource_dal
    ):
        with pytest.raises(AttributeMissingException):
            AttributeAdapter(
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

    def test_excluded_when_dal_resource_excluded(
        self, adapter, consolidated_config, consolidated_session, resource_dal
    ):
        resource_dal.tp_generation_enabled = True
        exclude_entity(
            consolidated_config._obj, consolidated_session.id, resource_dal.id
        )
        assert adapter.get() is False

    def test_set_updates_attribute(self, adapter, resource_dal):
        adapter.set(True)
        assert resource_dal.tp_generation_enabled is True
        adapter.set(False)
        assert resource_dal.tp_generation_enabled is False

    def test_custom_included_excluded_values(
        self, consolidated_config, consolidated_session, non_resource_dal
    ):
        non_resource_dal.sid = 1001
        adapter = AttributeAdapter(
            consolidated_config,
            consolidated_session,
            non_resource_dal,
            "sid",
            include_value=1001,
            exclude_value=1002,
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
        return AdjustableAttributeAdapter(
            consolidated_config, consolidated_session, dal, "trigger_rate_hz"
        )

    def test_rejects_missing_attribute(
        self, consolidated_config, consolidated_session, non_resource_dal
    ):
        with pytest.raises(AttributeMissingException):
            AdjustableAttributeAdapter(
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
