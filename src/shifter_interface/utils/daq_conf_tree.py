# Essentially the tree from https://github.com/DUNE-DAQ/daqconf/blob/develop/scripts/daqconf_inspector

import runconf_ui.interfaces.actions.actions as ca
from runconf_ui.interfaces.controller.config_wrapper import ConfigurationWrapper
from runconf_ui.interfaces.workflows.extract_system_info import (
    DetectorExtractor,
    SubsystemStatus,
)
from runconf_ui.exceptions import CiderBadActionException

from rich.tree import Tree
from abc import ABC, abstractmethod
from runconf_ui.interfaces.controller.application_controller import ShifterInterfaceState


class DaqConfTreeBase(ABC):
    """
    Base class for the daq conf tree
    """

    def __init__(
        self,
        application_controller: ShifterInterfaceState,
    ):
        """Constructor for the DaqConfTree class."""

        self._app_controller = application_controller

        self._tree = Tree("[bold red]No Configuration Loaded")
        self._disabled_objs = []
        self.open_new_session()

    def open_new_session(self):
        """Open a new session."""

        if (
            self._app_controller.dummy_oks_configuration is not None
            and self._app_controller.session_name is not None
        ):
            self.generate_tree()

    def print_tree(self):
        """Print the tree."""
        return self._tree

    def get_text_colour_message(self, system_state: SubsystemStatus | None):

        if system_state == SubsystemStatus.ENABLED:
            colour = "chartreuse4"
        elif (
            system_state == SubsystemStatus.DISABLED
            or system_state == SubsystemStatus.TOP_LEVEL_DISABLED
        ):
            system_state = SubsystemStatus.DISABLED
            colour = "grey35"
        elif system_state == SubsystemStatus.PARTIALLY_ENABLED:
            colour = "dark_orange3"
        else:
            raise ValueError(f"Invalid state {system_state}")

        # Just so we can make it readable!
        return colour, system_state.name.replace("_", " ")

    @abstractmethod
    def generate_tree(self):
        pass


class DaqConfTree(DaqConfTreeBase):
    """
    Class to represent the daq configuration tree. This generates the full system view
    """

    def __init__(
        self,
        application_controller: ShifterInterfaceState,
    ):
        """Constructor for the DaqConfTree class."""

        self._disabled_objs = []
        super().__init__(application_controller)

    def generate_tree(self) -> Tree:
        """Generate the tree."""
        # Add the session
        self._tree = Tree(f"[bold red1] {self._app_controller.session_name}")

        # We're now going to recurssively loop through relations to session
        session_dal = ca.GetDalObjectAction(
            self._app_controller.dummy_oks_configuration
        )(self._app_controller.session_name, "Session")

        self.build_tree(session_dal, self._tree, False)
        return self._tree

    def get_related_segments(self, segment):
        """
        Get related segments
        """
        class_name = ca.GetClassNameAction(
            self._app_controller.dummy_oks_configuration
        )(segment)

        # Inexplicably session labels its segments as "segments" and not "segment"
        if class_name == "Segment":
            return ca.GetAttributeAction(self._app_controller.dummy_oks_configuration)(
                segment, "segments"
            )
        elif class_name == "Session":
            return [
                ca.GetAttributeAction(self._app_controller.dummy_oks_configuration)(
                    segment, "segment"
                )
            ]
        else:
            raise ValueError(
                f"Invalid class {ca.GetClassNameAction(self._app_controller.dummy_oks_configuration)(segment)}"
            )

    def get_related_apps(self, segment):
        """
        Get related apps
        """
        return ca.GetAttributeAction(self._app_controller.dummy_oks_configuration)(
            segment, "applications"
        )

    def build_tree(self, segment, tree_branch: Tree, is_disabled: bool = False):
        # Get segmeents

        # Recurssive logic
        if not self.get_related_segments(segment):
            return

        if self.get_related_segments(segment):
            segs = tree_branch.add("[bold dark_orange3]Segments")

        # Loop through segments
        for seg in self.get_related_segments(segment):
            seg_name = ca.GetAttributeAction(
                self._app_controller.dummy_oks_configuration
            )(seg, "id")

            if (
                ca.CheckIsDisabledAction(self._app_controller.dummy_oks_configuration)(
                    seg, self._app_controller.session_name
                )
                or is_disabled
                or seg in self._disabled_objs
            ):
                seg_disabled = True
                colour = "grey35"
                message = "DISABLED"
            else:
                seg_disabled = False
                colour = "green"
                message = "ENABLED"

            seg_name = f"[{colour}]{seg_name}   [bold]{message}"
            seg_branch = segs.add(f"{seg_name}")

            # Continue building tree until nothing left
            self.build_tree(seg, seg_branch, seg_disabled)

            self.add_apps(seg, seg_branch, seg_disabled)
        return segs

    def add_apps(self, seg, seg_branch, seg_disabled):

        # Get apps
        if not len(self.get_related_apps(seg)):
            return

        seg_apps = seg_branch.add("[bold deep_pink4]Applications")
        for app in self.get_related_apps(seg):

            app_name = ca.GetAttributeAction(
                self._app_controller.dummy_oks_configuration
            )(app, "id")

            if (
                ca.CheckIsDisabledAction(self._app_controller.dummy_oks_configuration)(
                    app, self._app_controller.session_name
                )
                or seg_disabled
            ):
                colour = "grey35"
                message = "DISABLED"
                self._disabled_objs.append(app)

            else:
                colour = "green"
                message = "ENABLED"

            app_name = f"[{colour}]{app_name}   [bold]{message}"

            seg_apps.add(app_name)

    @property
    def disabled_objs(self):
        return self._disabled_objs


class ComponentLevelTree(DaqConfTreeBase):
    """
    Class to represent multi-component objects in a tree structure.
    """

    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        extractor: DetectorExtractor | None = None,
        disabled_items=[],
    ):
        self._extractor = extractor
        self._disabled_items = disabled_items

        super().__init__(application_controller)

    def generate_tree(self) -> Tree:
        """Generate the tree structure for the system."""
        if self._extractor is None:
            self._tree = Tree("[bold red1] No Configuration Loaded")
        else:
            self.initialise_tree()
        return self._tree

    def initialise_tree(self):
        self._tree = Tree(
            f"[bold red1] {self._extractor.system_info.get('view_panel', 'Unknown')}"
        )

        for system in self._extractor.systems:
            # Start with is_disabled=False for the top-level system
            try:
                self._add_system_to_tree(system, is_disabled=False)
            except CiderBadActionException:
                continue
            except Exception as e:
                raise e

    def _add_system_to_tree(self, system, is_disabled: bool):
        """Add a system and its subsystems to the tree."""
        # If the system is disabled, propagate the disabled state to all children

        state = self._extractor.get_state(system.system_name)

        # DON'T ADD
        if state == SubsystemStatus.STATE_NOT_DEFINED:
            return

        system_disabled = is_disabled or state == SubsystemStatus.DISABLED

        colour, message = self.get_text_colour_message(state)

        system_tree = self._tree.add(f"[{colour}]{system.system_name} [bold]{message}")

        for subsyst in system.system_names[::-1]:
            self._add_subsystem_to_tree(system, subsyst, system_tree, system_disabled)

    def _add_subsystem_to_tree(self, system, subsyst, system_tree, is_disabled: bool):
        """Add a subsystem and its components to the tree."""
        # If the subsystem is disabled, propagate the disabled state to all children
        state = system.get_state(subsyst)

        if state == SubsystemStatus.STATE_NOT_DEFINED:
            return

        subsystem_disabled = is_disabled or (state == SubsystemStatus.DISABLED)
        colour, message = self.get_text_colour_message(
            SubsystemStatus.DISABLED if subsystem_disabled else state
        )

        if subsyst != system.system_names[-1]:
            subsyst_tree = system_tree.add(f"[{colour}]{subsyst}   [bold]{message}")
        else:
            subsyst_tree = system_tree

        self._add_components_to_tree(system, subsyst, subsyst_tree, subsystem_disabled)
        self._add_attributes_to_tree(system, subsyst, subsyst_tree, subsystem_disabled)

    def _add_components_to_tree(self, system, subsyst, subsyst_tree, is_disabled: bool):
        """Add components of a subsystem to the tree."""
        for comp in system.get_components(subsyst):
            if subsyst == system.system_names[-1] and comp.system_name is not None:
                continue

            state = comp.get_state()

            if state == SubsystemStatus.STATE_NOT_DEFINED:
                continue

            component_disabled = (
                is_disabled
                or (state == SubsystemStatus.DISABLED)
                or comp.get_dal() in self._disabled_items
            )

            colour, message = self.get_text_colour_message(
                SubsystemStatus.DISABLED if component_disabled else state
            )
            subsyst_tree.add(f"[{colour}]{comp.system_id}   [bold]{message}")

    def _add_attributes_to_tree(self, system, subsyst, subsyst_tree, is_disabled: bool):
        """Add attributes and their affected objects to the tree."""
        attribute_objs = self._get_unique_attribute_objects(system, subsyst)
        attribute_tree = self._build_attribute_tree(attribute_objs, is_disabled)

        for attr in system.get_attributes(subsyst):
            if subsyst == system.system_names[-1] and attr.system_name is not None:
                continue

            self._add_attribute_to_tree(attr, attribute_tree, is_disabled)

        for attr_tree in attribute_tree.values():
            subsyst_tree.add(attr_tree)

    def _get_unique_attribute_objects(self, system, subsyst):
        """Get unique attribute objects for a subsystem."""
        attribute_objs = []
        for attr in system.get_attributes(subsyst):
            attribute_objs.extend(attr.get_affected_object_dals())

        return list(set(attribute_objs))

    def _build_attribute_tree(self, attribute_objs, system_disabled: bool = False):
        """Build a tree structure for attribute objects."""
        attribute_tree = {}
        for obj in attribute_objs:
            obj_id = ca.GetAttributeAction(
                self._app_controller.dummy_oks_configuration
            )(obj, "id")
            # Check if the attribute object is in the disabled list
            obj_disabled = obj in self._extractor.get_disabled_dals() or system_disabled

            status = (
                SubsystemStatus.DISABLED if obj_disabled else SubsystemStatus.ENABLED
            )

            colour, _ = self.get_text_colour_message(status)

            attribute_tree[obj_id] = Tree(f"[{colour}]{obj_id}")

        return attribute_tree

    def _add_attribute_to_tree(self, attr, attribute_tree, is_disabled: bool):
        """Add an attribute and its affected objects to the attribute tree."""
        for obj_name in attr.get_affected_object_names():
            if obj_name in attribute_tree:
                # If the attribute object is in the disabled list, mark it as disabled
                obj_disabled = (
                    is_disabled
                    or (attr.get_state_for_obj(obj_name) == SubsystemStatus.DISABLED)
                    or (attr.get_affected_object(obj_name) in self._disabled_items)
                )
                colour, message = self.get_text_colour_message(
                    SubsystemStatus.DISABLED
                    if obj_disabled
                    else attr.get_state_for_obj(obj_name)
                )
                attribute_tree[obj_name].add(
                    f"[{colour}]{attr.system_id}   [bold]{message}"
                )
