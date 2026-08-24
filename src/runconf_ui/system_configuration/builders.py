"""
Builders that assemble Group trees from structured configuration dataclasses.

A builder takes a system definition (from the YAML dataclasses) and returns
a fully constructed Group tree ready for traversal, indexing, and rendering.

Flag conventions used throughout:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - votes
     - propagate
     - Meaning
   * - ``True``
     - ``True``
     - Normal disable child; influences parent state and is set when parent
       is set. (default)
   * - ``False``
     - ``True``
     - Controlled-but-non-voting; gated by parent and set when parent is set,
       but doesn't influence parent state. Replaces the old
       ``controlled_objects`` mechanism.
   * - ``False``
     - ``False``
     - Adjustable child; fully independent of the enable/disable tree. Never
       set via ``Group.set()``.

Root strategy:

- ``subsystem_dependent=False`` — ``strategy=all``: system is on iff ALL components are on.
- ``subsystem_dependent=True`` — ``strategy=any``: system is on if ANY subsystem is on
  (equivalently, off only when ALL subsystems are off).
"""

from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.state_tree import Group
from runconf_ui.utils import get_logger

from .dataclasses import (
    AdjustableAttributeData,
    DisableableSystemData,
    DisableAttributeData,
    DisableElementData,
    DisableRelationshipData,
)
from .factories import (
    AdjustableFactory,
    AttributeFactory,
    ComponentFactory,
    RelationshipFactory,
)

# ---------------------------------------------------------------------------
# Disable system builder
# ---------------------------------------------------------------------------


class DisableSystemBuilder:
    """
    Builds a Group tree from a DisableableSystemData instance.

    When subsystem_dependent=False the root uses AND semantics: the system is
    on iff every voting child is on.

    When subsystem_dependent=True the root uses OR semantics: the system is on
    if any named subsystem is on, and goes off only when every subsystem is off.
    Subsystems created via at() always use OR semantics (a subsystem is on if
    any of its components are on).
    """

    def __init__(self, configuration: Configuration, session: DalBase):
        """Initialize DisableSystemBuilder.

        :param configuration: The conffwk Configuration object
        :param session: The session DAL object
        """
        get_logger().debug("Initialising DisableSystemBuilder")
        args = (configuration, session)
        self.component_factory = ComponentFactory(*args)
        get_logger().debug("   - component_factory intiialised")
        self.attribute_factory: AttributeFactory = AttributeFactory(*args)
        get_logger().debug("   - attribute_factory intiialised")
        self.relationship_factory = RelationshipFactory(*args)
        get_logger().debug("   - relationship_factory intiialised")

    def build(self, system: DisableableSystemData, label: str) -> Group:
        """Build a Group tree from system data.

        :param system: The system definition to build from
        :param label: Label for the root group
        :returns: The constructed Group tree
        :rtype: Group
        """
        root = Group(label=label)

        for comp in system.components:
            get_logger().debug(f"            - adding component: {comp} ")
            self._add_component(root, comp)

        for attr in system.attributes:
            get_logger().debug(f"            - adding attribute: {attr} ")
            self._add_attribute(root, attr)

        for rel in system.relationships:
            get_logger().debug(f"            - adding relationship: {rel} ")
            self._add_relationship(root, rel)

        return root

    # ------------------------------------------------------------------ #
    def _add_component(
        self,
        root: Group,
        comp: DisableElementData,
    ) -> None:
        """Add component nodes to the root group.

        :param root: The root group to add components to
        :param comp: The component element data
        :param subsystem_dependent: Whether the system is subsystem dependent
        """
        nodes = self.component_factory.create(comp)
        if not nodes:
            return

        for node in nodes:
            if comp.each_component_separate:
                # wrapper = Group(label=comp.system_label or node.label)
                # node.label = ""
                # wrapper.add(node)
                root.add(node)
            else:
                label = comp.system_label or (
                    node.label if comp.separate_system else ""
                )
                if label:
                    root.at(label).add(node)
                else:
                    root.add(node)

    def _add_attribute(
        self,
        root: Group,
        attr: DisableAttributeData,
    ) -> None:
        """Add attribute nodes to the root group.

        :param root: The root group to add attributes to
        :param attr: The attribute element data
        :param subsystem_dependent: Whether the system is subsystem dependent
        """
        node = self.attribute_factory.create(attr)
        if node is None:
            return

        label = attr.system_label

        if label:
            root.at(label).add(node)
        else:
            root.add(node)

    def _add_relationship(
        self,
        root: Group,
        rel: DisableRelationshipData,
    ) -> None:
        """Add relationship nodes to the root group.

        :param root: The root group to add relationships to
        :param rel: The relationship element data
        :param subsystem_dependent: Whether the system is subsystem dependent
        """
        node = self.relationship_factory.create(rel)
        if node is None:
            return

        label = rel.system_label

        if label:
            root.at(label).add(node)
        else:
            root.add(node)


# ---------------------------------------------------------------------------
# Adjustable system builder
# ---------------------------------------------------------------------------


class AdjustableSystemBuilder:
    """
    Builds a Group tree from a list of AdjustableAttributeData instances.
    """

    def __init__(self, configuration: Configuration, session: DalBase):
        """Initialize AdjustableSystemBuilder.

        :param configuration: The conffwk Configuration object
        :param session: The session DAL object
        """
        get_logger().debug("Initialising AdjustableSystemBuilder")
        self.factory = AdjustableFactory(configuration, session)

    def build(self, attributes: list[AdjustableAttributeData], label: str) -> Group:
        """Build a Group tree from adjustable attribute data.

        :param attributes: List of adjustable attribute definitions
        :param label: Label for the root group
        :returns: The constructed Group tree
        :rtype: Group
        """
        root = Group(label=label)
        get_logger().debug("Building adjustable attributes")

        for attr in attributes:
            get_logger().debug(f"    - Building {attr}")

            nodes = self.factory.create(attr)
            for node in nodes or []:
                root.add(node)

        return root
