import pytest

from runconf_ui import state_operations
from runconf_ui.exceptions import (
    AttributeMissingException,
    AttributeValueException,
    DuplicatedSubsystemException,
    IncompatibleDalException,
    StateBindingError,
    SubsystemLabelError,
)

'''
Low level tests of the enable/disable framework
'''

# ---------------------------------------------------------------------------
# DAL fixtures
# ---------------------------------------------------------------------------

def make_dal_fixture(dal_type, dal_name):
    '''
    Helper ¿meta-function? that will dynamically produce fixtures to avoid lots of boiler plate
    '''
    @pytest.fixture
    def dal(consolidated_config):
        return consolidated_config.get_dal(dal_type, dal_name)
    return dal

ru_01_dal = make_dal_fixture('ReadoutApplication', 'ru-01')
ru_02_dal = make_dal_fixture('ReadoutApplication', 'ru-02')
ru_segment_dal = make_dal_fixture('Segment', 'ru-segment')

# We'll use this for dummy tests
df_segment_dal = make_dal_fixture('Segment', 'df-segment')

# ---------------------------------------------------------------------------
# Toggle fixtures
# ---------------------------------------------------------------------------

def make_resource_toggle(dal_fixture, label):
    @pytest.fixture
    def toggle(consolidated_config, consolidated_session, request):
        dal = request.getfixturevalue(dal_fixture)
        return state_operations.DisableResource(consolidated_config, consolidated_session, dal, label=label)
    return toggle

def make_attribute_toggle(dal_fixture, attribute):
    @pytest.fixture
    def toggle(consolidated_config, consolidated_session, request):
        dal = request.getfixturevalue(dal_fixture)
        return state_operations.DisableAttribute(consolidated_config, consolidated_session, dal, attribute)
    return toggle

ru_01_resource_toggle = make_resource_toggle('ru_01_dal', 'ru_01')
ru_02_resource_toggle = make_resource_toggle('ru_02_dal', 'ru_02')
ru_segment_toggle     = make_resource_toggle('ru_segment_dal', 'ru_segment')
ru_01_tpg_toggle      = make_attribute_toggle('ru_01_dal', 'tp_generation_enabled')
ru_02_tpg_toggle      = make_attribute_toggle('ru_02_dal', 'tp_generation_enabled')

df_system_toggle = make_resource_toggle('df_segment_dal', 'df_segment')

# ---------------------------------------------------------------------------
# Container fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app_container(consolidated_config, consolidated_session, request):
    ops = [request.getfixturevalue(f) for f in ('ru_01_resource_toggle', 'ru_02_resource_toggle')]
    return state_operations.StateOperationContainerOr(
        consolidated_config, consolidated_session,
        label="applications",
        state_operations=ops,
    )

@pytest.fixture
def readout_segment(consolidated_config, consolidated_session, app_container, ru_segment_toggle):
    return state_operations.StateOperationContainerAnd(
        consolidated_config, consolidated_session,
        label="readout",
        state_operations=[app_container, ru_segment_toggle],
    )

@pytest.fixture
def full_system(consolidated_config, consolidated_session, readout_segment, ru_01_tpg_toggle, ru_02_tpg_toggle):
    system = state_operations.SystemContainer(consolidated_config, consolidated_session, 'ReadoutSubsystem')
    system.add_to_subsystem('ru-seg', readout_segment)
    system.add_to_subsystem('ru_01_tpg', ru_01_tpg_toggle),
    
    # Bit silly but let's add ru_02 to our controlled objects
    system.add_controlled_object(ru_02_tpg_toggle)
    
    return system

# ---------------------------------------------------------------------------
# Generic Failure tests
# ---------------------------------------------------------------------------
def test_attribute_failures(consolidated_config, consolidated_session, ru_01_dal):
    with pytest.raises(AttributeMissingException):
        state_operations.DisableAttribute(consolidated_config, consolidated_session, ru_01_dal, 'dummy attribute')


def test_adjustable_attributes(consolidated_config, consolidated_session):
    adjustable_dal = consolidated_config.get_dal("SourceIDConf", "tp-srcid-1001")
    
    attribute_obj = state_operations.AdjustableAttribute(consolidated_config,
                                                         consolidated_session,
                                                         adjustable_dal, 'sid')
    
    init_state = attribute_obj.get_state()
    
    attribute_obj.set_state(1067)
    assert attribute_obj.get_state() == 1067
    
    attribute_obj.set_state(init_state)
    assert attribute_obj.get_state() == init_state
    
def test_disable_resource_failure(consolidated_config, consolidated_session):
    
    dummy_dal = consolidated_config.get_dal("SourceIDConf", "tp-srcid-1001")

    with pytest.raises(IncompatibleDalException):
        state_operations.DisableResource(consolidated_config, consolidated_session, dummy_dal)
    
# ---------------------------------------------------------------------------
# Enable/Disable Tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("toggle_fixture", ["ru_01_resource_toggle", "ru_01_tpg_toggle"])
def test_disable_simple_operator(toggle_fixture, request, ru_02_resource_toggle):
    '''
    Test the enable/disable on simple operators
    '''
    ru_02_resource_toggle.set_state(True)

    operator = request.getfixturevalue(toggle_fixture)

    operator.set_state(False)
    assert not operator.get_state()
    # Ensure no side effects
    assert ru_02_resource_toggle.get_state()


    operator.set_state(True)
    assert operator.get_state()
    assert ru_02_resource_toggle.get_state()

    with pytest.raises(AttributeValueException):
        operator.set_state("dummy")

def test_related_dal(ru_01_resource_toggle, ru_01_tpg_toggle):
    '''
    For attributes of a dal, check the disabling the dal disables the attributee
    '''
    
    ru_01_tpg_toggle.set_state(True)
    ru_01_resource_toggle.set_state(True)
    assert ru_01_tpg_toggle.get_state()
    
    ru_01_resource_toggle.set_state(False)
    assert not ru_01_tpg_toggle.get_state()

    # Invert to test toggle back on
    ru_01_resource_toggle.set_state(True)
    assert ru_01_tpg_toggle.get_state()
    

def test_or_group(app_container, ru_01_resource_toggle, ru_02_resource_toggle):
    '''
    Test objects stored in an OR group
    '''
    app_container.set_state(True)
    ru_01_resource_toggle.set_state(True)
    ru_02_resource_toggle.set_state(True)
    
    
    ru_01_resource_toggle.set_state(False)
    assert app_container.get_state()
    assert ru_02_resource_toggle.get_state()
    
    ru_02_resource_toggle.set_state(False)
    assert not app_container.get_state()
    
    app_container.set_state(True)
    assert ru_01_resource_toggle.get_state()
    assert ru_02_resource_toggle.get_state()
    
    # And check toggle reverse
    app_container.set_state(False)
    assert not ru_01_resource_toggle.get_state()
    assert not ru_02_resource_toggle.get_state()

    # Now we know this works only need to reset here!
    app_container.set_state(True)

def test_and_group(app_container, ru_segment_toggle, readout_segment):
    '''
    Test objects stored in an AND group
    '''
    readout_segment.set_state(True)
    app_container.set_state(True)
    ru_segment_toggle.set_state(True)
    
    app_container.set_state(False)
    assert not ru_segment_toggle.get_state()
    assert not readout_segment.get_state()
    
    readout_segment.set_state(True)
    assert app_container.get_state()
    assert ru_segment_toggle.get_state()

def test_full_system(full_system, app_container, ru_02_tpg_toggle):
    # First let's check the subsystem registry

    assert set(full_system.subsystem_registry) == {'ru-seg', 'ru_01_tpg'}
    
    # Testing the actual classes is somewhat tricky, so let's check the keys correspond to the labels
    assert set(full_system.get_nested_registry().keys()) == {'ru-seg', 
                                                             'ru_01_tpg',
                                                             'readout',
                                                             'applications',
                                                             'ru_segment',
                                                             'ru_01',
                                                             'ru_02'}
    
    # Now we can try
    apps = full_system.get_system('applications')
    # Test retrieval
    assert apps == app_container
    
    # Check to see if can recognsise poor label formatting
    with pytest.raises(SubsystemLabelError):
        full_system.get_subsystem('not real!')
    
    with pytest.raises(SubsystemLabelError):
        full_system.get_system('APPLICATIONS')
    
    # Check for binding errors
    with pytest.raises(StateBindingError):
        ru_02_tpg_toggle.set_state(False)
    
    # Reset everything
    full_system.set_state(True)
    assert app_container.get_state()
    assert ru_02_tpg_toggle.get_state()
    
    full_system.set_state(False)
    assert not app_container.get_state()
    assert not ru_02_tpg_toggle.get_state()

    full_system.set_state(True)

    with pytest.raises(StateBindingError):
        ru_02_tpg_toggle.bind_state(full_system)

    assert ru_02_tpg_toggle.get_internal_state() == full_system.get_state()
    
  

def test_append_objects(full_system):
    ru_subsystem = full_system.get_subsystem('ru-seg')
    toggle = full_system.controlled_objects[0]
    
    # Check we don't change things!
    assert full_system.state_operations.count(ru_subsystem)==1
    full_system.add_state_operation(ru_subsystem)
    assert full_system.state_operations.count(ru_subsystem)==1
    
    assert full_system.controlled_objects.count(toggle) == 1
    full_system.add_controlled_object(toggle)
    assert full_system.controlled_objects.count(toggle) == 1

def test_subsyst_defined_correctly(full_system, df_system_toggle):
    '''
    Check if error gets thrown if a subsystem has the same name as
    a DAL
    '''
    with pytest.raises(DuplicatedSubsystemException):
        full_system.add_to_subsystem('ru_01', df_system_toggle)
    

def test_duplicate_labels(full_system, df_system_toggle):
    # We make a dummy dal
    # Get a repeat key
    used_key = next(iter(full_system.get_nested_registry()))
    
    df_lab = df_system_toggle.label
    df_system_toggle.label = used_key
    
    with pytest.raises(DuplicatedSubsystemException):
        full_system.add_state_operation(df_system_toggle)
    
    # Reset
    df_system_toggle.label = df_lab