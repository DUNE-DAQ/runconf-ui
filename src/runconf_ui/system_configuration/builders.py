"""
Builders that assemble Group trees from structured configuration dataclasses.

A builder takes a system definition (from the YAML dataclasses) and returns
a fully constructed Group tree ready for traversal, indexing, and rendering.

Flag conventions used throughout:

  votes=True,  propagate=True  — normal disable child; influences parent state
                                 and is set when parent is set. (default)
  votes=False, propagate=True  — controlled-but-non-voting; gated by parent
                                 and set when parent is set, but doesn't
                                 influence parent state.
                                 Replaces the old controlled_objects mechanism.
  votes=False, propagate=False — adjustable child; fully independent of the
                                 enable/disable tree. Never set via Group.set().

Root strategy:
  subsystem_dependent=False — strategy=all (system is on iff ALL components are on)
  subsystem_dependent=True  — strategy=any (system is on if ANY subsystem is on;
                               equivalently, off only when ALL subsystems are off)
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
        root_strategy = any if system.subsystem_dependent else all
        root = Group(label=label, strategy=root_strategy)

        for comp in system.components:
            get_logger().debug(f"            - adding component: {comp} ")
            self._add_component(root, comp, system.subsystem_dependent)

        for attr in system.attributes:
            get_logger().debug(f"            - adding attribute: {attr} ")
            self._add_attribute(root, attr, system.subsystem_dependent)

        for rel in system.relationships:
            get_logger().debug(f"            - adding relationship: {rel} ")
            self._add_relationship(root, rel, system.subsystem_dependent)

        return root

    # ------------------------------------------------------------------ #
    def _votes(self, subsystem_dependent: bool, has_own_label: bool) -> bool:
        """
        A child votes iff the system is not subsystem_dependent, or the child
        has its own named label (i.e. it is itself a named subsystem).
        """
        return not subsystem_dependent or has_own_label

    def _add_component(
        self,
        root: Group,
        comp: DisableElementData,
        subsystem_dependent: bool,
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
                # Wrap each leaf in a named container Group.
                # The leaf's label is cleared so only the Group appears as a button.
                # votes=False on root → root stays vacuously True, never gating siblings.
                # propagate=True on root → toggling root still reaches all containers.
                wrapper = Group(label=comp.system_label or node.label, strategy=any)
                node.label = ""
                wrapper.add(node, votes=True, propagate=True)
                root.add(wrapper, votes=False, propagate=True)
            else:
                label = comp.system_label or (
                    node.label if comp.separate_system else ""
                )
                votes = self._votes(subsystem_dependent, bool(label))
                if label:
                    root.at(label).add(node, votes=True, propagate=True)
                else:
                    root.add(node, votes=votes, propagate=True)

    def _add_attribute(
        self,
        root: Group,
        attr: DisableAttributeData,
        subsystem_dependent: bool,
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
        votes = self._votes(subsystem_dependent, bool(label or attr.separate_system))

        if label:
            root.at(label).add(node, votes=True, propagate=True)
        else:
            root.add(node, votes=votes, propagate=True)

    def _add_relationship(
        self,
        root: Group,
        rel: DisableRelationshipData,
        subsystem_dependent: bool,
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
        votes = self._votes(subsystem_dependent, bool(label or rel.separate_system))

        if label:
            root.at(label).add(node, votes=True, propagate=True)
        else:
            root.add(node, votes=votes, propagate=True)


# ---------------------------------------------------------------------------
# Adjustable system builder
# ---------------------------------------------------------------------------


class AdjustableSystemBuilder:
    """
    Builds a Group tree from a list of AdjustableAttributeData instances.

    All children use votes=False, propagate=False — they are never touched
    by Group.set() and do not influence any parent's aggregated state.
    Their visible state (ENABLED / PARENT_DISABLED) is computed by
    compute_state() in traversal.py based on parent group state and
    DAL resource state.
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
        root = Group(label=label, strategy=all)
        get_logger().debug("Building adjustable attributes")

        for attr in attributes:
            get_logger().debug(f"    - Building {attr}")

            nodes = self.factory.create(attr)
            if not nodes:
                continue
            for node in nodes:
                root.add(node, votes=False, propagate=False)

        return root
