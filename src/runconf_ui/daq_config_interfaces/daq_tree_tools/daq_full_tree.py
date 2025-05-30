
# from runconf_ui.daq_config_interfaces.daq_tree_tools.daq_conf_tree import DaqConfTreeBase
# from runconf_ui.runconf_ui_controllers.runconf_ui_state import ShifterInterfaceState
# from rich.tree import Tree
# import runconf_ui.daq_config_interfaces.actions.actions as ca
# import logging
# from typing import Optional

# class DaqFullTree(DaqConfTreeBase):
#     def __init__(
#         self,
#         application_controller: ShifterInterfaceState,
#         class_filters: Optional[list[str]] = None,
#     ):
#         """Constructor for the DaqFullTree class."""
#         self._class_filters = class_filters if class_filters is not None else []

#         # Quick swap to DAL objects        
#         if self._class_filters and application_controller.buffer_daq_config is not None:
#             filt = []
#             for f in self._class_filters:
#                 filt.extend(ca.GetDalsOfClassAction(application_controller.buffer_daq_config)(f))

#             self._class_filters = filt
        
#         super().__init__(application_controller)


#     def generate_tree(self) -> Tree:
#         """Generate the tree structure for the system."""
        
#         if self._application_controller.current_daq_config is None:
#             return Tree("[bold red]No DAQ configuration loaded[/bold red]")
        
#         self._tree = Tree(f"[bold red]Configuration: [/bold red]")
        
#         sessions = ca.GetDalsOfClassAction(self._application_controller.buffer_daq_config)("Session")
        
#         for s in sessions:
#             session_name = ca.GetAttributeAction(self._application_controller.buffer_daq_config)(s, "id")
#             session_tree = self._tree.add(f"[bold green]{session_name}[/bold green] [blue]Session[/blue]")
#             self.build_tree(session_tree, s, session_name=session_name)
    
#     def check_class_filter(self, dal_obj) -> bool:
#         """Check if the DAL object matches the class filters."""
#         if not self._class_filters:
#             return True
        
#         return dal_obj in self._class_filters
    
#     def build_tree(self, branch: Tree, dal_obj, is_disabled: bool=False, session_name: str="")->Tree | None:
#         """Build the tree structure."""
#         logging.info(f"Building tree for {dal_obj}")
        
#         dal_class = ca.GetClassNameAction(self._application_controller.buffer_daq_config)(dal_obj)
#         dal_name = ca.GetAttributeAction(self._application_controller.buffer_daq_config)(dal_obj, "id")
        
#         if is_disabled and self.check_class_filter(dal_obj):
#             dal_branch = branch.add(f"[bold red]{dal_name}[/bold red] [yellow]{dal_class}[/yellow] [dim] (disabled)[/dim]")
#         elif self.check_class_filter(dal_obj):
#             dal_branch = branch.add(f"[bold green]{dal_name}[/bold green] [blue]{dal_class}[/blue]")
#         else:
#             dal_branch = branch
            
            
#         for relationship in ca.GetRelatedDalsAction(self._application_controller.buffer_daq_config)(dal_obj):
#             filtered_relationships = [
#                 rel for rel in list(relationship.values())[0] if
#                 self.check_class_filter(rel) and list(relationship.keys())[0] != "disabled"
#             ]
            
#             if not filtered_relationships:
#                 continue
        
#             rel_branch = dal_branch.add(f"[bold cyan]{list(relationship.keys())[0]}[/bold cyan]")
            
#             for r in filtered_relationships:
#                 dal_is_disabled = r in self._disabled_objs or is_disabled
#                 # try:
#                 dal_is_disabled = ca.CheckIsDisabledAction(self._application_controller.buffer_daq_config)(r, session_name) \
#                                     or dal_is_disabled
            
#                 self.build_tree(rel_branch, r, dal_is_disabled, session_name=session_name)
        
#     @property
#     def disabled_objs(self):
#         """Get the list of disabled objects."""
#         return self._disabled_objs

from runconf_ui.daq_config_interfaces.daq_tree_tools.daq_conf_tree import DaqConfTreeBase
from runconf_ui.runconf_ui_controllers.runconf_ui_state import ShifterInterfaceState
from rich.tree import Tree
import runconf_ui.daq_config_interfaces.actions.actions as ca
import logging
from typing import Optional, Set

class DaqFullTree(DaqConfTreeBase):
    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        class_filters: Optional[list[str]] = None,
    ):
        """Optimized constructor for the DaqFullTree class."""
        self._class_filters = set(class_filters) if class_filters else set()

        # Quick swap to DAL objects        
        if self._class_filters and application_controller.buffer_daq_config is not None:
            new_filters = set()
            for f in self._class_filters:
                new_filters.update(ca.GetDalsOfClassAction(application_controller.buffer_daq_config)(f))
            self._class_filters = new_filters
        
        super().__init__(application_controller)

    def generate_tree(self) -> Tree:
        """Generate the tree structure for the system with optimizations."""
        if self._application_controller.current_daq_config is None:
            return Tree("[bold red]No DAQ configuration loaded[/bold red]")
        
        self._tree = Tree("[bold red]Configuration: [/bold red]")
        buffer = self._application_controller.buffer_daq_config
        get_sessions = ca.GetDalsOfClassAction(buffer)
        get_attribute = ca.GetAttributeAction(buffer)
        
        sessions = get_sessions("Session")
        
        for s in sessions:
            session_name = get_attribute(s, "id")
            session_tree = self._tree.add(f"[bold green]{session_name}[/bold green] [blue]Session[/blue]")
            self.build_tree(session_tree, s, session_name=session_name)
    
    def check_class_filter(self, dal_obj) -> bool:
        """Optimized class filter check using set membership."""
        return not self._class_filters or dal_obj in self._class_filters
    
    def build_tree(self, branch: Tree, dal_obj, is_disabled: bool = False, session_name: str = "") -> Tree | None:
        """Optimized tree building with reduced method calls and caching."""
        buffer = self._application_controller.buffer_daq_config
        get_class_name = ca.GetClassNameAction(buffer)
        get_attribute = ca.GetAttributeAction(buffer)
        get_related_dals = ca.GetRelatedDalsAction(buffer)
        check_disabled = ca.CheckIsDisabledAction(buffer)
        
        logging.info(f"Building tree for {dal_obj}")
        
        dal_class = get_class_name(dal_obj)
        dal_name = get_attribute(dal_obj, "id")
        
        if not self.check_class_filter(dal_obj):
            dal_branch = branch
        else:
            if is_disabled:
                dal_branch = branch.add(f"[bold red]{dal_name}[/bold red] [yellow]{dal_class}[/yellow] [dim] (disabled)[/dim]")
            else:
                dal_branch = branch.add(f"[bold green]{dal_name}[/bold green] [blue]{dal_class}[/blue]")
            
        for relationship in get_related_dals(dal_obj):
            rel_name = next(iter(relationship.keys()))
            related_objects = relationship[rel_name]
            
            # Filter in one pass
            filtered_relationships = [
                r for r in related_objects
                if self.check_class_filter(r) and rel_name != "disabled"
            ]
            
            if not filtered_relationships:
                continue
        
            rel_branch = dal_branch.add(f"[bold cyan]{rel_name}[/bold cyan]")
            
            for r in filtered_relationships:
                dal_is_disabled = r in self._disabled_objs or is_disabled
                try:
                    dal_is_disabled = check_disabled(r, session_name) or dal_is_disabled
                except Exception:
                    logging.warning(f"Error checking if {r} is disabled, skipping", exc_info=True)
            
                self.build_tree(rel_branch, r, dal_is_disabled, session_name=session_name)
        
    @property
    def disabled_objs(self) -> Set:
        """Get the set of disabled objects."""
        return self._disabled_objs