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
"""

from runconf_ui.state_tree import Group

from .dataclasses import (
    AdjustableAttributeData,
    DisableAttributeData,
    DisableElementData,
    DisableRelationshipData,
    DisableableSystemData,
)
from .factories import (
    AdjustableFactory,
    AttributeFactory,
    ComponentFactory,
    RelationshipFactory,
)

from conffwk import Configuration
from conffwk.dal import DalBase



# ---------------------------------------------------------------------------
# Disable system builder
# ---------------------------------------------------------------------------

class DisableSystemBuilder:
    """
    Builds a Group tree from a DisableableSystemData instance.

    The root Group uses AND semantics (system is on iff all voting children
    are on). Subsystems created via at() use OR semantics (a subsystem is on
    if any of its components are on).
    """

    def __init__(self, configuration: Configuration, session: DalBase):
        args = (configuration, session)
        self.component_factory    = ComponentFactory(*args)
        self.attribute_factory    = AttributeFactory(*args)
        self.relationship_factory = RelationshipFactory(*args)

    def build(self, system: DisableableSystemData, label: str) -> Group:
        root = Group(label=label, strategy=all)

        for comp in system.components:
            self._add_component(root, comp, system.subsystem_dependent)

        for attr in system.attributes:
            self._add_attribute(root, attr, system.subsystem_dependent)

        for rel in system.relationships:
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
        nodes = self.component_factory.create(comp)
        if not nodes:
            return

        for node in nodes:
            label = comp.system_label or (node.label if comp.separate_system else "")
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
        self.factory = AdjustableFactory(configuration, session)

    def build(self, attributes: list[AdjustableAttributeData], label: str) -> Group:
        root = Group(label=label, strategy=all)

        for attr in attributes:
            nodes = self.factory.create(attr)
            if not nodes:
                continue
            for node in nodes:
                root.add(node, votes=False, propagate=False)

        return root