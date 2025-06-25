from runconf_ui.runconf_ui_controllers.runconf_ui_state import ShifterInterfaceState
import runconf_ui.daq_config_interfaces.actions.actions as ca
from typing import Set
from runconf_ui.utils.subsystem_status import SubsystemStatus
from runconf_ui.daq_config_interfaces.daq_tree_tools.daq_conf_tree import ConfigTree, ConfigTreeBranch
from runconf_ui.runconf_ui_configuration.object_extractors.detector_extractor import (
    DetectorExtractor,
)

class ComponentLevelTree(ConfigTree):
    """
    Component level tree generator that builds a tree structure for the DAQ configuration
    at the component level.
    This class is optimized for performance and memory usage.
    """
    def __init__(self, application_controller: ShifterInterfaceState, extractor: DetectorExtractor ):
        """Initialize the ComponentLevelTree with the application controller."""
        
        
        # Get the session
        self._application_controller = application_controller
        self._extractor = extractor
        
        # Handle the case where no DAQ configuration is loaded
        root_branch = ConfigTreeBranch(
            self._extractor.system_info.get('view_panel', 'Unknown View Panel'),
            self._extractor.system_info.get('view_panel', 'Unknown View Panel'),
            SubsystemStatus.NOT_A_SUBSYSTEM
        )
        
        super().__init__(root_branch)
        
    def generate_tree(self):
        # Start with the root branch
        self.reset_tree()
        
        for system in self._extractor.systems:
            state = self._extractor.get_state(system)
            
            # Add a full system!
            system_branch = ConfigTreeBranch(
                system.system_name,
                system.system_name,
                state
            )
            self.add_branch(self.get_root(), system_branch)
            self._generate_subsytem_branch(system_branch, system)
    
    def _generate_subsytem_branch(self, parent_branch: ConfigTreeBranch, system):
        """Generate the component level branch."""
        # We ALWAYS assume that the parent branch contains a DAL object
        if parent_branch.state == SubsystemStatus.NOT_A_SUBSYSTEM:
            return
        # First we add components
        for subsystem in system.system_names[::-1]:
            if subsystem != system.system_names[-1]:
                # we have a subsystem, so we create a new branch
                subsystem_branch = ConfigTreeBranch(
                    subsystem,
                    subsystem,
                    self._extractor.get_state(subsystem)
                )
            else:
                # Add to the parent branch
                subsystem_branch = parent_branch
                    
            self._add_components(subsystem_branch, system)
            self._add_attributes(subsystem_branch, system)
            
            # If the subsystem branch has no children, we remove it
            if len(subsystem_branch.get_children()) == 0:
                self.remove_branch(subsystem_branch)
        
    def _add_components(self, parent_branch: ConfigTreeBranch, system):
        """Add components to the parent branch."""
        
        # Get the components from the extractor
        components = system.get_components(parent_branch.id)
        
        for component in components:
            state = component.get_state()
            if state == SubsystemStatus.STATE_NOT_DEFINED:
                # Skip components that are not defined
                continue
            
            component_branch = ConfigTreeBranch(
                component.system_id,
                component.system_id,
                state
            )
            self.add_branch(parent_branch, component_branch)
    
    def _add_attributes(self, parent_branch: ConfigTreeBranch, system):
        attributes = system.get_attributes(parent_branch.id)
        
        for attribute in attributes:
            self._add_attribute_branch(attribute, parent_branch)


    def _add_attribute_branch(self, attribute, parent_branch: ConfigTreeBranch):
        '''
        Make structure of dal->attribute
        '''
        attribute_state = attribute.get_state()
        
        if attribute_state == SubsystemStatus.STATE_NOT_DEFINED:
            # Skip attributes that are not defined
            return
        
        attribute_branch = ConfigTreeBranch(
            attribute.system_id,
            attribute.system_id,
            attribute_state
        )
        
        # Add the attribute branch with NO parent
        self.add_branch(None, attribute_branch)
        
        for dal_obj in attribute.get_affected_object_dals():
            self.add_dal_branch(dal_obj, parent_branch, attribute_branch, attribute_state)

    def add_dal_branch(self, dal_obj, parent_branch, attribute_branch, attribute_state):
        obj_id = ca.GetAttributeAction(self._application_controller.buffer_daq_config)(dal_obj, "id")
        obj_class = ca.GetClassNameAction(self._application_controller.buffer_daq_config)(dal_obj)
        
        session = ca.GetDalsOfClassAction(self._application_controller.buffer_daq_config)("Session")[0]
        session_id = ca.GetAttributeAction(self._application_controller.buffer_daq_config)(session, "id")
        
        
        dal_disabled = ca.CheckIsDisabledAction(self._application_controller.buffer_daq_config)(dal_obj, session_id)

        if dal_disabled or attribute_state == SubsystemStatus.DISABLED:
            dal_state = SubsystemStatus.DISABLED
        else:
            dal_state = SubsystemStatus.ENABLED
        
        dal_obj_branch = ConfigTreeBranch(
            obj_class,
            obj_id,
            dal_state
        )
        
        # Add the DAL object branch to the parent branch
        self.add_branch(parent_branch, dal_obj_branch)
        # Add the attribute as a CHILD of the DAL object branch
        self.add_branch(dal_obj_branch, attribute_branch)
