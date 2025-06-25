from runconf_ui.runconf_ui_configuration.object_extractors.extractor_interfaces import (
    MultiItemExtractor,
    SubsystemExtractor,
)
from runconf_ui.runconf_ui_configuration.object_extractors.attribute_extractor import (
    AttributeExtractor,
)
from runconf_ui.runconf_ui_configuration.object_extractors.component_extractor import (
    ComponentExtractor,
)
from runconf_ui.runconf_ui_configuration.object_extractors.relationship_extractor import (
    RelationshipExtractor,
)
from runconf_ui.utils.subsystem_status import SubsystemStatus
from runconf_ui.exceptions import CiderBadActionException
import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)

from typing import Dict, Sequence, Optional, List
import logging
import traceback

class SystemExtractor(MultiItemExtractor):
    """
    Extracts and manages system state including attributes, components, and subsystems.
    
    Handles hierarchical system structures where systems can contain multiple subsystems,
    and provides methods to enable/disable systems and query their states.
    """

    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        system_name: Optional[str],
        system: Optional[Dict],
        disabled_dals: List = None,
    ):
        """
        Initialize SystemExtractor.
        
        :param application_controller: Application controller interface
        :param system_name: Name of system
        :param system: Dictionary containing system information
        :param disabled_dals: List of disabled dals, defaults to []
        
        System structure:
        {
            "subsystem_dependent": bool,  # If all subsystems are disabled, disable this system
            "attributes": [<list of attribute subsystems>],
            "components": [<list of component subsystems>],
            "relationships": [<list of relationship subsystems>]
        }
        """
        # Initialize collections
        self._attributes: List[AttributeExtractor] = []
        self._components: List[ComponentExtractor] = []
        self._system_names: List[str] = []
        
        # System configuration
        self._system_name = system_name
        self._subsystem_dependent = False
        self._display_full_system = True
        
        # Caching for performance
        self._tooltips: Dict[str, str] = {}
        self._subsystems: Dict[str, List] = {}
        self._component_cache: Dict[str, List] = {}
        self._attribute_cache: Dict[str, List] = {}
        
        # Initialize tooltip for main system
        if self._system_name:
            self._tooltips["full_syst"] = f"Enable/disable {self._system_name}"
        
        super().__init__(application_controller, system, disabled_dals or [])

    def read_system(self, system: Dict, system_name: Optional[str] = None) -> bool:
        """
        Read dictionary containing system information and extract state.
        
        :param system: System configuration dictionary
        :param system_name: Optional override for system name
        :return: True if system was read successfully
        """
        if not super().read_system(system):
            logging.error(f"System with name {system_name} is not valid, cannot read system.")
            return False

        # Update system name if provided
        if system_name is not None:
            self._system_name = system_name

        logging.debug(f"Reading system {self._system_name}")

        # Extract system configuration
        self._subsystem_dependent = system.get("subsystem_dependent", False)
        self._display_full_system = system.get("display_full_system", True)

        # Process attributes and relationships
        self._extract_attributes(system)
        self._extract_components(system)
        self._build_system_structure()
        
        return True

    def _extract_attributes(self, system: Dict) -> None:
        """Extract attributes and relationships from system configuration."""
        self._attributes = []
        
        # Add regular attributes
        for attr_config in system.get("attributes", []):
            self._attributes.append(
                AttributeExtractor(self._application_controller, attr_config)
            )
        
        # Add relationships
        for rel_config in system.get("relationships", []):
            self._attributes.append(
                RelationshipExtractor(self._application_controller, rel_config)
            )

    def _extract_components(self, system: Dict) -> None:
        """Extract components from system configuration."""
        self._components = []
        
        for comp_config in system.get("components", []):
            if comp_config.get("each_component_separate", False):
                self._extract_multi_component(comp_config)
            else:
                self._add_component(comp_config)

    def _extract_multi_component(self, comp_config: Dict) -> None:
        """Extract multiple components from a wildcard configuration."""
        component_names = self.find_components_with_wildcard(
            comp_config["id"], comp_config["class"]
        )
        
        for comp_name in component_names:
            # Create a copy and modify for this specific component
            modified_config = comp_config.copy()
            modified_config["id"] = comp_name
            
            # Set up separate system if needed
            if not modified_config.get("separate_system", False):
                modified_config["system_label"] = comp_name
                modified_config["separate_system"] = True
            
            self._add_component(modified_config)

    def _add_component(self, comp_config: Dict) -> None:
        """Add a single component to the system."""
        # Set up tooltip for separate systems
        extractor = ComponentExtractor(self._application_controller, comp_config)

        if comp_config.get("separate_system", False):
            system_label = comp_config["system_label"]
            # Create and add component if not filtered
            self._tooltips[system_label] = extractor.tooltip
        

        if not extractor.is_filtered():
            self._components.append(extractor)

    def _build_system_structure(self) -> None:
        """Build the internal system structure and caches."""
        # Get all system names from subsystems
        all_subsystems = self._attributes + self._components
        self._system_names = list({
            subsystem.system_name 
            for subsystem in all_subsystems 
            if subsystem.is_system
        })
        
        # Add main system name
        if self._system_name:
            self._system_names.append(self._system_name)
        else:
            self._system_names.append("root")
        
        # Build subsystem mappings
        self._subsystems = {}
        for system_name in self._system_names:
            components = self._get_components_for_system(system_name)
            attributes = self._get_attributes_for_system(system_name)
            self._subsystems[system_name] = [components, attributes]
        
        # Build tooltips for subsystems
        for system_name in self._system_names:
            if system_name not in self._tooltips:
                # Get first available tooltip from components or attributes
                all_items = [*self._get_components_for_system(system_name), 
                           *self._get_attributes_for_system(system_name)]
                if all_items:
                    self._tooltips[system_name] = all_items[0].tooltip
        
        # Clear caches after rebuild
        self._component_cache.clear()
        self._attribute_cache.clear()
        
        logging.debug(f"System names: {self._system_names}")

    def _get_components_for_system(self, system_name: str) -> List:
        """Get components for a specific system."""
        return [
            comp for comp in self._components
            if self._subsystem_matches(comp, system_name)
        ]

    def _get_attributes_for_system(self, system_name: str) -> List:
        """Get attributes for a specific system."""
        return [
            attr for attr in self._attributes
            if self._subsystem_matches(attr, system_name)
        ]

    def _subsystem_matches(self, subsystem: SubsystemExtractor, system_name: str) -> bool:
        """Check if a subsystem belongs to the specified system."""
        if system_name in [None, self._system_name]:
            return True
        return subsystem.system_name == system_name

    def extract_components(self, system: Dict) -> None:
        """Legacy method name - delegates to _extract_components for compatibility."""
        self._extract_components(system)

    @property
    def system_names(self) -> Sequence[str]:
        """Get all system names in this extractor."""
        return self._system_names

    @property
    def system_name(self) -> Optional[str]:
        """Get the main system name."""
        return self._system_name

    def _get_state(self, system_name: Optional[str] = None) -> Optional[SubsystemStatus]:
        """
        Get state of the system or subsystem.
        
        :param system_name: Name of the system to check, defaults to main system
        :return: Current state or None if not available
        """
        target_system = system_name or self._system_name
        
        # Check for top-level disabling
        if self._is_top_level_disabled(system_name):
            return SubsystemStatus.TOP_LEVEL_DISABLED
        
        # Handle subsystem-dependent systems
        if target_system == self._system_name and self._subsystem_dependent:
            subsystem_state = self._get_subsystem_state()
            if subsystem_state != SubsystemStatus.STATE_NOT_DEFINED:
                return subsystem_state
        
        # Get states for the target system
        return self._calculate_system_state(target_system)

    def _is_top_level_disabled(self, system_name: Optional[str]) -> bool:
        """Check if system is disabled at top level."""
        if system_name == self._system_name or not self._subsystem_dependent:
            return False
        
        main_state = self._calculate_system_state(self._system_name)
        return main_state in [SubsystemStatus.DISABLED, SubsystemStatus.TOP_LEVEL_DISABLED]

    def _calculate_system_state(self, system_name: str) -> SubsystemStatus:
        """Calculate the current state of a system based on its subsystems."""
        subsystem_groups = self._subsystems.get(system_name, [])
        
        # Flatten and filter valid states
        all_states = []
        for group in subsystem_groups:
            for subsystem in group:
                state = subsystem.get_state()
                if state != SubsystemStatus.STATE_NOT_DEFINED:
                    all_states.append(state)
        
        if not all_states:
            logging.debug(f"No valid states found for {system_name}")
            return SubsystemStatus.STATE_NOT_DEFINED
        
        # Check if all states are the same
        if len(set(all_states)) == 1:
            return all_states[0]
        
        logging.debug(f"Mixed states found for {system_name}, returning PARTIALLY_ENABLED")
        return SubsystemStatus.PARTIALLY_ENABLED

    def _get_subsystem_state(self) -> SubsystemStatus:
        """Get the collective state of all system-level subsystems."""
        system_subsystems = [
            subsystem for subsystem in self._attributes + self._components
            if subsystem.is_system and subsystem.get_state() != SubsystemStatus.STATE_NOT_DEFINED
        ]
        
        if not system_subsystems:
            return SubsystemStatus.STATE_NOT_DEFINED
        
        states = [subsystem.get_state() for subsystem in system_subsystems]
        
        # Return uniform state or partially enabled
        return states[0] if len(set(states)) == 1 else SubsystemStatus.PARTIALLY_ENABLED

    def _set_state(self, state: SubsystemStatus, system_name: Optional[str]) -> None:
        """Set state for a system and its subsystems."""
        target_system = system_name or self._system_name
        
        # Handle subsystem-dependent behavior
        if self._subsystem_dependent:
            self._set_full_system_state(state, target_system)
        
        # Set state for all subsystems in the target system
        subsystem_groups = self._subsystems.get(target_system, [])
        for group in subsystem_groups:
            for subsystem in group:
                subsystem.set_state(state)

    def _set_full_system_state(self, state: SubsystemStatus, system_name: Optional[str]) -> None:
        """
        Set state for non-subsystem components based on subsystem dependencies.
        
        This handles the complex logic of enabling/disabling global components
        based on the state of other subsystems.
        """
        if not system_name:
            return
        
        # Get states of other subsystems
        other_system_states = [
            subsystem.get_state()
            for subsystem in self._attributes + self._components
            if (subsystem.is_system and 
                subsystem.get_state() != SubsystemStatus.STATE_NOT_DEFINED and
                subsystem.system_name != system_name)
        ]
        
        # Determine the effective state for non-system components
        effective_state = state
        if other_system_states and not all(s == state for s in other_system_states):
            effective_state = SubsystemStatus.ENABLED
        
        # Apply state to non-system components
        for subsystem in self._attributes + self._components:
            if not subsystem.is_system:
                subsystem.set_state(effective_state)

    def get_all_states(self) -> Dict[str, SubsystemStatus]:
        """
        Get the state of the system and any nested subsystems.
        
        :return: Dictionary mapping system names to their states
        """
        if (not self._application_controller.session_name or 
            not self._application_controller.buffer_daq_config):
            return {}

        result = {}
        
        # Add main system state if configured to display
        if self._display_full_system and self._system_name:
            main_state = self.get_state()
            if main_state is not None:
                result[self._system_name] = main_state
        
        # Add subsystem states
        for system_name in sorted(self._system_names):
            if system_name in [None, self._system_name]:
                continue
            try:
                state = self.get_state(system_name)
                if state is not None:
                    result[system_name] = state
            except CiderBadActionException:
                logging.debug(f"Could not get state for {system_name} in {self.system_name}")
            except Exception as e:
                logging.error(f"Error getting state for {system_name}: {e}")
                logging.error(traceback.format_exc())
        
        return result

    def get_components(self, system_name: Optional[str] = None) -> List:
        """
        Get components for a specific system.
        
        :param system_name: System name to filter by, defaults to all
        :return: List of matching components
        """
        # Use cache if available
        cache_key = system_name or "all"
        if cache_key in self._component_cache:
            return self._component_cache[cache_key]
        
        # Calculate and cache result
        result = [
            comp for comp in self._components
            if self._subsystem_matches(comp, system_name)
        ]
        self._component_cache[cache_key] = result
        return result

    def get_attributes(self, system_name: Optional[str] = None) -> List:
        """
        Get attributes for a specific system.
        
        :param system_name: System name to filter by, defaults to all
        :return: List of matching attributes
        """
        # Use cache if available
        cache_key = system_name or "all"
        if cache_key in self._attribute_cache:
            return self._attribute_cache[cache_key]
        
        # Calculate and cache result
        result = [
            attr for attr in self._attributes
            if self._subsystem_matches(attr, system_name)
        ]
        self._attribute_cache[cache_key] = result
        return result

    def set_disabled_dals(self, disabled_dals: List) -> None:
        """
        Set disabled DALs for the system and all subsystems.
        
        :param disabled_dals: List of disabled DAL identifiers
        """
        super().set_disabled_dals(disabled_dals)
        
        # Propagate to all subsystems
        for subsystem in self._attributes + self._components:
            subsystem.set_disabled_dals(disabled_dals)

    def find_components_with_wildcard(self, wildcard: str, class_name: str) -> List[str]:
        """
        Find components with a wildcard pattern in the system.
        
        :param wildcard: Wildcard pattern to search for
        :param class_name: Class name to filter by
        :return: List of component IDs that match the wildcard
        """
        # Get all DALs of the specified class
        dals = ca.GetDalsOfClassAction(self._application_controller.buffer_daq_config)(
            class_name
        )
        
        if not dals:
            return []
        
        # Filter by wildcard pattern
        matching_components = []
        for dal in dals:
            component_id = ca.GetAttributeAction(self._application_controller.buffer_daq_config)(
                dal, "id"
            )
            if wildcard in component_id:
                matching_components.append(component_id)
        
        return matching_components

    def get_tooltip(self, system_name: Optional[str] = None) -> str:
        """
        Get the tooltip for the system or subsystem.
        
        :param system_name: Name of the system to get tooltip for
        :return: Tooltip text
        """
        if system_name is None:
            return self._tooltips.get(
                "full_syst", f"Enable/Disable {self._system_name or 'System'}"
            )
        
        if self._tooltips.get(system_name):
            return self._tooltips[system_name]
        else:
            return f"Enable/Disable {system_name}"
