import pytest

from runconf_ui import state_operations
from runconf_ui.exceptions import (
    AttributeMissingException,
    AttributeValueException,
    IncompatibleDalException,
)

# ---------------------------------------------------------------------------
# Helpers / constants
# ---------------------------------------------------------------------------

READOUT_RESOURCES = [
    ("ru-01", "ReadoutApplication", "tp_generation_enabled"),
    ("ru-02", "ReadoutApplication", "tp_generation_enabled"),
]


SEGMENT_CLASS = "Segment"
SEGMENT_UID = "ru-segment"

def _make_disable_resource(config, session, class_name, uid):
    return state_operations.DisableResource(
        config,
        session,
        config.get_dal(class_name, uid),
    )

def _make_disable_attribute(config, session, class_name, uid, attribute,
                            enabled_state=True, disabled_state=False):

    return state_operations.DisableAttribute(
            config,
            session,
            config.get_dal(class_name, uid),
            attribute,
            enabled_state,
            disabled_state,
        )
    

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def generate_disable_resource_list(consolidated_config, consolidated_session):
    cfg, sess = consolidated_config, consolidated_session

    readout_ops = [
        _make_disable_resource(cfg, sess, class_name, uid)
        for uid, class_name ,_ in READOUT_RESOURCES
    ]

    readout_collection = state_operations.StateOperationContainerOr(
        cfg, sess, readout_ops
    )

    segment_op = _make_disable_resource(cfg, sess, SEGMENT_CLASS, SEGMENT_UID)

    readout_segment = state_operations.StateOperationContainerAnd(
        cfg, sess, [readout_collection, segment_op]
    )

    for op in [*readout_ops, segment_op]:
        op.set_state(True)

    return {
        "readout_ops": readout_ops,
        "readout_collection": readout_collection,
        "segment_op": segment_op,
        "readout_segment": readout_segment,
    }
    
@pytest.fixture(scope="session")
def generate_disable_attribute_list(consolidated_config, consolidated_session):
    config, session = consolidated_config, consolidated_session
    return [
            _make_disable_attribute(config, session, class_name, uid, attribute) 
                for uid, class_name, attribute in READOUT_RESOURCES
            ]

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# Generic failure modes
def test_non_resource_failure(consolidated_config, consolidated_session):
    '''Check if we get an error when we don't make a resource'''
    with pytest.raises(IncompatibleDalException):
        assert _make_disable_resource(consolidated_config,
                            consolidated_session,
                            'Variable',
                            'local-env-ers-warning'), "Must raise an error if you try and make a non-resource disableable"

def test_missing_attribute(consolidated_config, consolidated_session):
    with pytest.raises(AttributeMissingException):
        assert _make_disable_attribute(consolidated_config,
                                        consolidated_session,
                                        'Variable',
                                        'local-env-ers-warning',
                                        'dummy_attribute'), "Must raise an error if you try and make a non-resource disableable"


def test_resource_equality(generate_disable_resource_list):
    resource_ops = generate_disable_resource_list["readout_ops"]
    
    assert resource_ops[0] == resource_ops[0]
    assert resource_ops[1] != resource_ops[0]
    assert resource_ops[1] == resource_ops[1]


def test_resource_list(generate_disable_resource_list):
    ops = generate_disable_resource_list
    readout_ops = ops["readout_ops"]
    readout_collection = ops["readout_collection"]
    segment_op = ops["segment_op"]
    readout_segment = ops["readout_segment"]

    all_ops = [*readout_ops, readout_collection, segment_op, readout_segment]

    # All resources start enabled
    assert all(op.get_state() for op in all_ops)

    # Disabling one readout should not yet affect the OR-collection or segment
    readout_ops[0].set_state(False)
    assert not readout_ops[0].get_state()
    assert all(op.get_state() for op in [*readout_ops[1:], readout_collection, segment_op])

    # Disabling all readouts collapses the OR-collection and the AND-container
    for op in readout_ops[1:]:
        op.set_state(False)
    assert not any(op.get_state() for op in readout_ops)
    assert segment_op.get_state(), "Segment should still be enabled independently"
    assert not readout_segment.get_state(), "AND-container requires all children enabled"

    # Re-enabling the segment (and implicitly verifying the full container recovers)
    for op in readout_ops:
        op.set_state(True)
    assert all(op.get_state() for op in all_ops)


def test_attributes(generate_disable_resource_list, generate_disable_attribute_list):
    readout_segment = generate_disable_resource_list["readout_segment"]

    readout_before = len(readout_segment.contained_operations)

    for attribute_op in generate_disable_attribute_list:
        attribute_op.set_state(False)
        readout_segment.add_state_operation(attribute_op)
    
    readout_segment.set_state(False)
    
    assert not all(op.dal_enabled() for op in generate_disable_attribute_list)
    assert not all(op.get_state() for op in generate_disable_attribute_list)

    # Make sure are actually dealing with the same thing!
    assert len(readout_segment.contained_operations) == readout_before+len(generate_disable_attribute_list), f"List length must increase by {len(generate_disable_attribute_list)}"

    readout_segment.add_state_operation(generate_disable_attribute_list[0])
    # Check the list length hasn't changed
    assert len(readout_segment.contained_operations) == readout_before+len(generate_disable_attribute_list), "Duplicates cannot be added to the list!"

    readout_segment.set_state(True)
    assert all(op.dal_enabled() for op in generate_disable_attribute_list)
    assert all(op.get_state() for op in generate_disable_attribute_list)

    
def test_incorrect_attribute(generate_disable_attribute_list):
        with pytest.raises(AttributeValueException):
            assert generate_disable_attribute_list[0].set_state("dummy")

def test_adjustable_attribute_values(consolidated_config, consolidated_session):
    adjustable_attribute = state_operations.AdjustableAttribute(
        consolidated_config,
        consolidated_session,
        consolidated_config.get_dal(
            'Service', 'dataRequests'
        ),
        'port'
    )
    
    adjustable_attribute.set_state(100)
    assert adjustable_attribute.get_state() == 100
    adjustable_attribute.set_state(0)

    # Test wrong type completely
    with pytest.raises(ValueError):
        adjustable_attribute.set_state("not a proper value")