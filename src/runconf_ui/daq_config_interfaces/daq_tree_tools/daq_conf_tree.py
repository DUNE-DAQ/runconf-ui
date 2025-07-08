#  version focusing on caching and reduced object creation

import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.runconf_ui_configuration.object_extractors.detector_extractor import (
    DetectorExtractor,
)
from runconf_ui.utils.subsystem_status import SubsystemStatus
from runconf_ui.exceptions import CiderBadActionException
from rich.tree import Tree
from abc import ABC, abstractmethod
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)


class DaqConfTreeBase(ABC):
    """
     base class for the daq conf tree with caching support
    """

    def __init__(self, application_controller: ShifterInterfaceState):
        """Constructor for the DaqConfTreeBase class."""
        self._application_controller = application_controller
        self._tree = Tree("[bold red]No Configuration Loaded")
        self._tree_nodes = {"TOP_LEVEL": self._tree}
        self._disabled_objs = []
        
        # Caching for expensive operations
        self._colour_cache = {}
        self._state_cache = {}
        self._config_hash = None
        self._last_tree = None
        
        # Pre-compute action objects to avoid repeated instantiation
        self._actions_cache = {}
        
        self.open_new_session()

    def _get_action(self, action_class):
        """Cache action objects to avoid repeated instantiation."""
        if action_class not in self._actions_cache:
            self._actions_cache[action_class] = action_class(
                self._application_controller.buffer_daq_config
            )
        return self._actions_cache[action_class]

    def _get_config_hash(self):
        """Generate a simple hash of the current configuration to detect changes."""
        if self._application_controller.buffer_daq_config is None:
            return None
        # Use id() as a simple change detector - you might want something more sophisticated
        return id(self._application_controller.buffer_daq_config)

    def open_new_session(self):
        """Open a new session with change detection."""
        current_hash = self._get_config_hash()
        
        # Only regenerate if configuration changed
        if current_hash != self._config_hash:
            self._config_hash = current_hash
            self._clear_caches()
            
            if (
                self._application_controller.buffer_daq_config is not None
                and self._application_controller.session_name is not None
            ):
                self.generate_tree()
        elif self._last_tree is not None:
            # Reuse the last tree if nothing changed
            self._tree = self._last_tree

    def _clear_caches(self):
        """Clear all caches when configuration changes."""
        self._colour_cache.clear()
        self._state_cache.clear()
        self._actions_cache.clear()
        self._last_tree = None

    def print_tree(self):
        """Print the tree."""
        return self._tree

    def get_text_colour_message(self, system_state: SubsystemStatus | None):
        """Cached version of colour/message lookup."""
        if system_state in self._colour_cache:
            return self._colour_cache[system_state]

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

        result = (colour, system_state.name.replace("~", " "))
        self._colour_cache[system_state] = result
        return result

    @abstractmethod
    def generate_tree(self):
        pass


class ComponentLevelTree(DaqConfTreeBase):
    """
     class to represent multi-component objects in a tree structure.
    """

    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        extractor: DetectorExtractor | None = None,
        disabled_items=None,
    ):
        self._extractor = extractor
        self._disabled_items = set(disabled_items or [])  # Use set for O(1) lookup
        super().__init__(application_controller)

    def generate_tree(self) -> Tree:
        """Generate the tree structure for the system with caching."""
        if self._extractor is None:
            self._tree = Tree("[bold red1] No Configuration Loaded")
        else:
            self.initialise_tree()
        
        # Cache the generated tree
        self._last_tree = self._tree
        return self._tree

    def initialise_tree(self):
        """Initialize tree with pre-computed strings."""
        system_info = self._extractor.system_info.get('view_panel', 'Unknown')
        self._tree = Tree(f"[bold red1] {system_info}")

        for system in self._extractor.systems:
            try:
                self._add_system_to_tree(system, is_disabled=False)
            except CiderBadActionException:
                continue
            except Exception as e:
                raise e

    def _add_system_to_tree(self, system, is_disabled: bool):
        """Add a system and its subsystems to the tree."""
        state = self._extractor.get_state(system.system_name)

        if state == SubsystemStatus.STATE_NOT_DEFINED:
            return

        system_disabled = is_disabled or state == SubsystemStatus.DISABLED
        colour, message = self.get_text_colour_message(state)

        # Pre-compute the formatted string
        system_label = f"[{colour}]{system.system_name} [bold]{message}"
        system_tree = self._tree.add(system_label)

        # Process subsystems in reverse order as per original
        for subsyst in reversed(system.system_names):
            self._add_subsystem_to_tree(system, subsyst, system_tree, system_disabled)

    def _add_subsystem_to_tree(self, system, subsyst, system_tree, is_disabled: bool):
        """Add a subsystem and its components to the tree."""
        state = system.get_state(subsyst)

        if state == SubsystemStatus.STATE_NOT_DEFINED:
            return

        subsystem_disabled = is_disabled or (state == SubsystemStatus.DISABLED)
        colour, message = self.get_text_colour_message(
            SubsystemStatus.DISABLED if subsystem_disabled else state
        )

        if subsyst != system.system_names[-1]:
            subsyst_label = f"[{colour}]{subsyst}   [bold]{message}"
            subsyst_tree = system_tree.add(subsyst_label)
        else:
            subsyst_tree = system_tree

        self._add_components_to_tree(system, subsyst, subsyst_tree, subsystem_disabled)
        self._add_attributes_to_tree(system, subsyst, subsyst_tree, subsystem_disabled)

    def _add_components_to_tree(self, system, subsyst, subsyst_tree, is_disabled: bool):
        """Add components of a subsystem to the tree with batch processing."""
        components = system.get_components(subsyst)
        
        # Pre-filter components to avoid repeated checks
        valid_components = [
            comp for comp in components
            if not (subsyst == system.system_names[-1] and comp.system_name is not None)
            and comp.get_state() != SubsystemStatus.STATE_NOT_DEFINED
        ]

        # Batch process components
        component_labels = []
        for comp in valid_components:
            state = comp.get_state()
            component_disabled = (
                is_disabled
                or (state == SubsystemStatus.DISABLED)
                or comp.get_dal() in self._disabled_items
            )

            colour, message = self.get_text_colour_message(
                SubsystemStatus.DISABLED if component_disabled else state
            )
            component_labels.append(f"[{colour}]{comp.system_id}   [bold]{message}")

        # Add all components at once
        for label in component_labels:
            subsyst_tree.add(label)

    def _get_unique_attribute_objects(self, system, subsyst):
        """Get unique attribute objects for a subsystem, ensuring they are referenced by at least one attribute."""
        attribute_objs = set()
        attributes = system.get_attributes(subsyst)
        
        for attr in attributes:
            affected_objs = attr.get_affected_object_dals()
            if affected_objs:
                attribute_objs.update(affected_objs)
        
        return list(attribute_objs)

    def _build_attribute_tree(self, attribute_objs, system_disabled: bool = False):
        """Build a tree structure for attribute objects with cached actions."""
        get_attribute_action = self._get_action(ca.GetAttributeAction)
        disabled_dals = self._extractor.get_disabled_dals()
        
        attribute_tree = {}
        for obj in attribute_objs:
            obj_id = get_attribute_action(obj, "id")

            obj_disabled = obj in disabled_dals or system_disabled
            status = SubsystemStatus.DISABLED if obj_disabled else SubsystemStatus.ENABLED
            colour, _ = self.get_text_colour_message(status)

            attribute_tree[obj_id] = Tree(f"[{colour}]{obj_id}")

        return attribute_tree

    def _add_attributes_to_tree(self, system, subsyst, subsyst_tree, is_disabled: bool):
        """Add attributes and their affected objects to the tree with optimizations."""
        attribute_objs = self._get_unique_attribute_objects(system, subsyst)
        
        if not attribute_objs:
            return

        attribute_tree = self._build_attribute_tree(attribute_objs, is_disabled)
        has_attributes = False

        # Pre-filter attributes
        attributes = system.get_attributes(subsyst)
        valid_attributes = [
            attr for attr in attributes
            if not (subsyst == system.system_names[-1] and attr.system_name is not None)
            and attr.get_affected_object_names()
        ]

        for attr in valid_attributes:
            self._add_attribute_to_tree(attr, attribute_tree, is_disabled)
            has_attributes = True

        if has_attributes:
            for attr_tree in attribute_tree.values():
                subsyst_tree.add(attr_tree)

    def _add_attribute_to_tree(self, attr, attribute_tree, is_disabled: bool):
        """Add an attribute to the attribute tree with pre-computed labels."""
        affected_object_names = attr.get_affected_object_names()
        
        for obj_name in affected_object_names:
            if obj_name in attribute_tree:
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
                
                attr_label = f"[{colour}]{attr.system_id}   [bold]{message}"
                attribute_tree[obj_name].add(attr_label)


