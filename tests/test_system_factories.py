
from runconf_ui.system_configuration import (
    AdjustableAttributeData,
    DisableAttributeData,
    DisableElementData,
    DisableRelationshipData,
    FilterData,
)
from runconf_ui.system_configuration.factories import (
    AdjustableOperationFactory,
    AttributeOperationFactory,
    ComponentOperationFactory,
)
from runconf_ui.system_configuration.factories.relationship_operation_factory import (
    RelationshipOperationFactory,
)


def test_attribute_factory(consolidated_config, consolidated_session):
    # Set up dataclasses
    attr_data = DisableAttributeData(
        id='tp_generation_enabled',
        segments=["ru-segment"],
        class_name='ReadoutApplication',
        separate_system=True,
        system_label="ru-01",
    )

    atribute_fac = AttributeOperationFactory(consolidated_config, consolidated_session)

    attribute_objs = atribute_fac.create(attr_data)
    assert attribute_objs is not None

    dal_ids = {s.dal.id for s in attribute_objs[0].state_operations}
    assert dal_ids == {'ru-01', 'ru-02'}

    attr_data.segments = ["df-segment"]
    attribute_objs = atribute_fac.create(attr_data)
    assert attribute_objs is None


def test_str_to_dal(consolidated_config, consolidated_session):
    relationship_fac = RelationshipOperationFactory(consolidated_config, consolidated_session)

    assert relationship_fac._str_to_dal('ru-01', 'ReadoutApplication').id == 'ru-01'
    readout_dals = relationship_fac._str_to_dal(['ru-01', 'ru-02'], 'ReadoutApplication')
    assert {r.id for r in readout_dals} == {'ru-01', 'ru-02'}


def test_relationship_factory(consolidated_config, consolidated_session):
    relationship_fac = RelationshipOperationFactory(consolidated_config, consolidated_session)

    queue_rules = ['fa-queue-rule', 'tp-queue-rule', 'wib-eth-raw-data-rule', 'fd-dlh-data-requests-queue-rule']

    # Set up dataclasses
    rel_data = DisableRelationshipData(
        id='queue_rules',
        segments=["ru-segment"],
        class_name='ReadoutApplication',
        enabled_state=queue_rules,
        disabled_state=[],
        relationship_class='QueueConnectionRule',
        separate_system=True,
        system_label="ru-01",
    )

    rel_obj_list = relationship_fac.create(rel_data)
    assert rel_obj_list is not None

    assert {d.id for d in rel_data.enabled_state} == set(queue_rules)
    assert rel_data.disabled_state == []

    rel_obj = rel_obj_list[0]

    rel_obj.set_state(True)
    assert {r.id for d in rel_obj.state_operations for r in d.dal.queue_rules} == set(queue_rules)

    rel_obj.set_state(False)
    assert {r.id for d in rel_obj.state_operations for r in d.dal.queue_rules} == set()

    rel_obj.set_state(True)

    # Bad disabled_state should return None
    bad_rel_data = DisableRelationshipData(
        id='queue_rules',
        segments=["ru-segment"],
        class_name='ReadoutApplication',
        enabled_state=queue_rules,
        disabled_state='dummy',
        relationship_class='QueueConnectionRule',
        separate_system=True,
        system_label="ru-01",
    )
    assert relationship_fac.create(bad_rel_data) is None


def test_component_factory(consolidated_config, consolidated_session):
    component_factory = ComponentOperationFactory(consolidated_config, consolidated_session)

    # Set up dataclasses
    cmp_data = DisableElementData(
        id='ru-01',
        class_name='ReadoutApplication',
        each_component_separate=False,
    )

    single_obj = component_factory.create(cmp_data)
    assert single_obj[0].dal.id == 'ru-01'

    # Multiple components
    multi_data = DisableElementData(
        class_name='ReadoutApplication',
        each_component_separate=True,
    )

    multi_obj = component_factory.create(multi_data)
    assert {s.dal.id for s in multi_obj} == {'ru-01', 'ru-02'}
    assert {s.label for s in multi_obj} == {'ru-01', 'ru-02'}


def test_adjustable_factory(consolidated_config, consolidated_session):
    adj_factory = AdjustableOperationFactory(consolidated_config, consolidated_session)

    # Set up dataclasses
    adjustable_data = AdjustableAttributeData(
        id='tp-srcid-1001',
        class_name='SourceIDConf',
        attribute_name='sid',
    )

    adj_obj = adj_factory.create(adjustable_data)
    assert adj_obj[0].dal.id == "tp-srcid-1001"
    assert adj_obj[0].label == "tp-srcid-1001"

    # No id — should return all DALs of that class
    adjustable_data_no_id = AdjustableAttributeData(
        class_name='SourceIDConf',
        attribute_name='sid',
    )
    adj_obj = adj_factory.create(adjustable_data_no_id)
    assert len(adj_obj) == len(consolidated_config.get_dals(adjustable_data_no_id.class_name))

    # Unknown class/attribute should return None
    assert adj_factory.create(AdjustableAttributeData(class_name='dummy', attribute_name='dummy')) is None


def test_filtering(consolidated_config, consolidated_session):
    component_factory = ComponentOperationFactory(consolidated_config, consolidated_session)

    # Set up dataclasses
    filter_data = DisableElementData(
        class_name='ReadoutApplication',
        each_component_separate=True,
        filters=[FilterData(attribute="id", values=['ru-02'])],
    )

    obj_list = component_factory.create(filter_data)
    assert {s.dal.id for s in obj_list} == {'ru-01'}

    # Undefined filter attribute — should return all
    undefined_data = DisableElementData(
        class_name='ReadoutApplication',
        each_component_separate=True,
        filters=[FilterData(attribute="dummy", values=[0])],
    )

    obj_list = component_factory.create(undefined_data)
    assert {s.dal.id for s in obj_list} == {'ru-01', 'ru-02'}


def test_dal_resolver(consolidated_config, consolidated_session):
    component_factory = ComponentOperationFactory(consolidated_config, consolidated_session)

    # Set up dataclasses
    nonsense_data = DisableElementData(
        class_name='bad',
        id='bad',
    )

    assert component_factory.create(nonsense_data) is None

    nonsense_data.class_name = 'Segment'
    assert component_factory.create(nonsense_data) is None