from runconf_ui.daq_config_interfaces.daq_tree_tools.daq_conf_tree import (
    DaqConfTreeBase,
)
from runconf_ui.runconf_ui_controllers.runconf_ui_state import ShifterInterfaceState
from rich.tree import Tree
import runconf_ui.daq_config_interfaces.actions.actions as ca
import logging
from typing import Set, Optional
import logging


class DaqFullTree(DaqConfTreeBase):
    """ version of DaqFullTree with extensive caching."""
    
    def __init__(self, application_controller: ShifterInterfaceState):
        """ constructor with pre-computed filters."""
        self._class_filters = application_controller.shifter_interface_config.classes_to_show
        self._class_filter_set = set()
        
        if self._class_filters and application_controller.buffer_daq_config is not None:
            self._precompute_class_filters(application_controller.buffer_daq_config)
        
        super().__init__(application_controller)

    def _precompute_class_filters(self, buffer_config):
        """Pre-compute class filters as a set for O(1) lookup."""
        get_dals_action = ca.GetDalsOfClassAction(buffer_config)
        
        for filter_class in self._class_filters:
            try:
                self._class_filter_set.update(get_dals_action(filter_class))
            except Exception:
                continue

    def generate_tree(self) -> Tree:
        """Generate the tree structure with extensive caching."""
        if self._application_controller.current_daq_config is None:
            return Tree("[bold red]No DAQ configuration loaded[/bold red]")

        self._tree = Tree("[bold red]Configuration: [/bold red]")
        buffer = self._application_controller.buffer_daq_config
        
        # Cache action objects
        get_sessions_action = self._get_action(ca.GetDalsOfClassAction)
        get_attribute_action = self._get_action(ca.GetAttributeAction)

        sessions = get_sessions_action("Session")
        self._disabled_objs = []
        self._tree_nodes = {"TOP_LEVEL": self._tree}

        for session in sessions:
            session_name = get_attribute_action(session, "id")
            
            session_label = f"[bold green]{session_name}[/bold green] [blue]Session[/blue]"
            session_tree = self._tree.add(session_label)
            self._tree_nodes[f"{session_name}@Session"] = session_tree
            
            self.build_tree(session_tree, session, session_name=session_name)

        # Cache the result
        self._last_tree = self._tree
        return self._tree

    def check_class_filter(self, dal_obj) -> bool:
        """ class filter check using pre-computed set."""
        return not self._class_filter_set or dal_obj in self._class_filter_set

    def build_tree(
        self, 
        branch: Tree, 
        dal_obj, 
        is_disabled: bool = False, 
        session_name: str = ""
    ) -> Optional[Tree]:
        """ tree building with reduced string operations and caching."""
        # Use cached actions
        get_class_name_action = self._get_action(ca.GetClassNameAction)
        get_attribute_action = self._get_action(ca.GetAttributeAction)
        get_related_dals_action = self._get_action(ca.GetRelatedDalsAction)
        check_disabled_action = self._get_action(ca.CheckIsDisabledAction)

        dal_class = get_class_name_action(dal_obj)
        dal_name = get_attribute_action(dal_obj, "id")

        if not self.check_class_filter(dal_obj):
            dal_branch = branch
        else:
            # Pre-compute the label strings
            if is_disabled:
                dal_label = f"[bold red]{dal_name}[/bold red] [yellow]{dal_class}[/yellow] [dim] (disabled)[/dim]"
            else:
                dal_label = f"[bold green]{dal_name}[/bold green] [blue]{dal_class}[/blue]"
            
            dal_branch = branch.add(dal_label)
            self._tree_nodes[f"{dal_name}@{dal_class}"] = dal_branch

        relationships = get_related_dals_action(dal_obj)
        
        for relationship in relationships:
            rel_name = next(iter(relationship.keys()))
            related_objects = relationship[rel_name]

            # Single-pass filtering with early exit
            if rel_name == "disabled":
                continue
                
            filtered_relationships = [
                r for r in related_objects 
                if self.check_class_filter(r)
            ]

            if not filtered_relationships:
                continue

            rel_branch = dal_branch.add(f"[bold cyan]{rel_name}[/bold cyan]")

            # Batch process related objects
            for related_obj in filtered_relationships:
                dal_is_disabled = related_obj in self._disabled_objs or is_disabled
                
                try:
                    dal_is_disabled = check_disabled_action(related_obj, session_name) or dal_is_disabled
                except Exception:
                    logging.warning(
                        f"Error checking if {related_obj} is disabled, skipping", 
                        exc_info=True
                    )
                
                if dal_is_disabled:
                    self._disabled_objs.append(related_obj)

                self.build_tree(
                    rel_branch, 
                    related_obj, 
                    dal_is_disabled, 
                    session_name=session_name
                )

    @property
    def disabled_objs(self) -> Set:
        """Get the set of disabled objects."""
        return set(self._disabled_objs)


