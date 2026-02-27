'''
Wraps around runconf-ui, this "hides" most of the implementation details and handles the operations
required for file loading/opening
'''
from pathlib import Path
from dataclasses import dataclass

from rich.tree import Tree

from runconf_ui.exceptions import RunConfToolsRepoException, NodeNotFound
from runconf_ui.repo_manager import LocalRepoManager, RemoteRepoManager
from runconf_ui.state_tree import NodeStatus
from runconf_ui.system_configuration import SystemConfigReader
from runconf_ui.system_configuration.config_reader import AssembledConfig
from runconf_ui.utils import open_configuration
from runconf_ui.utils.rich_utils import draw_tree



@dataclass
class RunconfContext:
    '''
    Basic context runconf-ui needs
    '''
    apparatus: str
    conf_directory: Path
    use_local: bool
    default_config: str | None = None
    base_url: str | None = None
    ops_url: str | None = None


# view_panel label -> Rich Tree
TreeViews = dict[str, Tree]

class RunconfUI:
    '''
    Wrapper layer around RunConf-UI, this hides most of the operational details
    '''
    def __init__(self, context: RunconfContext):

        if context.use_local:
            self.repo_manager = LocalRepoManager(context.apparatus,
                                                 context.conf_directory)
        else:
            if any(d is None for d in (context.default_config, context.base_url, context.ops_url)):
                raise RunConfToolsRepoException(
                    "Error must set default config (blah.data.xml), base repo URL "
                    "and operations repo URL to use runconftools"
                )
            self.repo_manager = RemoteRepoManager(context.apparatus,
                                                  context.conf_directory,
                                                  context.default_config,
                                                  context.ops_url,
                                                  context.base_url)

        self.configuration = None
        self.system_config_reader: SystemConfigReader | None = None
        self._assembled: AssembledConfig | None = None


    def set_daq_version(self, version):
        self.repo_manager.set_daq_version(version)
        if version is not None:
            self.system_config_reader = SystemConfigReader(
                self.repo_manager.get_runconf_ui_config_path()
            )
        else:
            self.system_config_reader = None
            self.configuration = None
            self._assembled = None
            self._tree_views = None

    def get_daq_versions(self):
        return self.repo_manager.get_available_daq_versions()

    def select_session(self, session):
        if self.system_config_reader is None:
            raise RunConfToolsRepoException("No DAQ configuration setup, please select version first")

        self.configuration = open_configuration(self.repo_manager.select_config(session))

        self._assembled = self.system_config_reader.assemble_config(
            self.configuration,
            self.configuration.get_dals('Session')[0].id
        )
        # Build structural indexes once
        # Build initial tree views
        self.refresh_information()

    def get_sessions(self):
        return self.repo_manager.get_daq_sessions()


    # ------------------------------------------------------------------ #
    # Refresh                                                              #
    # ------------------------------------------------------------------ #

    def refresh_information(self) -> None:
        """
        Recompute the state of every node in the tree and rebuild the tree views.
        """
        if self._assembled is None:
            return

        for group in self._assembled.disableable:
            for node_status in group.nodes.values():
                node_status.refresh_state()
                
        self._tree_views = self._build_tree_views(self._assembled)
        
    # ------------------------------------------------------------------ #
    # Public API — disable                                                 #
    # ------------------------------------------------------------------ #

    def get_disable_index(self):
        """
        { group_label: { widget_id: IndexEntry, ... }, ... }
        Only DISABLE nodes. Returns empty dict if no config is loaded.
        """
        return self._assembled.disableable_nodes if self._assembled else {}

    def get_adjustable_index(self):
        """
        { group_label: { widget_id: IndexEntry, ... }, ... }
        Only ADJUSTABLE nodes. Returns empty dict if no config is loaded.
        """
        return self._assembled.adjustable_nodes if self._assembled else {}

    def toggle(self, widget_group: str, widget_id: str) -> None:
        """
        Toggle a disableable node
        """        
        node = self._resolve_node(self._assembled.disableable_nodes, widget_group, widget_id, "disableable")
        node.toggle()
        self.refresh_information()

    def get_disabled_node_states(self)->dict[str, dict[str, NodeStatus]]:
        """
        Get the current state of all disableable nodes.
        Returns a nested dict: { group_label: { widget_id: {'enabled': bool, 'interactive': bool}, ... }, ... }
        """
        if self._assembled is None:
            return {}        
        return self._assembled.disableable_nodes

    def get_adjustable_node_states(self)->dict[str, dict[str, NodeStatus]]:
        """
        Get the current state of all adjustable nodes.
        """
        if self._assembled is None:
            return {}        
        return self._assembled.adjustable_nodes

    def _resolve_node(self, collection: dict, group_label: str, widget_id: str, collection_name: str) -> NodeStatus:
        """
        Helper to fetch a NodeStatus from a collection (disableable/adjustable/all_nodes).
        Raises NodeNotFound with a short, consistent message when missing.
        """
        if self._assembled is None:
            raise NodeNotFound("No configuration loaded")

        group = collection.get(group_label, None)
        if group is None:
            available = list(collection.keys())
            raise NodeNotFound(f"Group {group_label!r} not found in {collection_name} nodes. Available groups: {available}")
        
        node = group.get(widget_id)
        if node is None:
            available = list(group.keys())
            raise NodeNotFound(f"Node {widget_id!r} not found in {collection_name} nodes for group {group_label!r}. Available: {available}")
        return node


    # ------------------------------------------------------------------ #
    # Public API — adjustable                               #
    # ------------------------------------------------------------------ #

    def _get_value(self, collection: dict, group_label: str, widget_id: str):
        """
        Get the current raw value of an ADJUSTABLE node.
        Raises TypeError if called on a DISABLE node.
        """
        node = self._resolve_node(collection, group_label, widget_id, "adjustable")
        return node.node.get()


    def _set_value(self, collection: dict, group_label: str, widget_id: str, value) -> None:
        """
        Set the raw value of an ADJUSTABLE node and return its refreshed IndexEntry.
        Raises TypeError if called on a DISABLE node.
        """
        node = self._resolve_node(collection, group_label, widget_id, "adjustable")
        node.node.set(value)
        self.refresh_information()
        
    def set_adjustable_value(self, widget_group: str, widget_id: str, value) -> None:
        """
        Set the raw value of an ADJUSTABLE node and return its refreshed IndexEntry.
        Raises TypeError if called on a DISABLE node.
        """
        self._set_value(self._assembled.adjustable_nodes, widget_group, widget_id, value)
        
    def get_adjustable_value(self, widget_group: str, widget_id: str):
        """
        Get the current raw value of an ADJUSTABLE node.
        Raises TypeError if called on a DISABLE node.
        """
        return self._get_value(self._assembled.adjustable_nodes, widget_group, widget_id)
    
    def set_disableable_value(self, widget_group: str, widget_id: str, value) -> None:
        """
        Set the raw value of a DISABLE node and return its refreshed IndexEntry.
        Raises TypeError if called on an ADJUSTABLE node.
        """
        self._set_value(self._assembled.disableable_nodes, widget_group, widget_id, value)
        
    def get_disableable_value(self, widget_group: str, widget_id: str):
        """
        Get the current raw value of a DISABLE node.
        Raises TypeError if called on an ADJUSTABLE node.
        """
        return self._get_value(self._assembled.disableable_nodes, widget_group, widget_id)
    
    def set_value(self, widget_group: str, widget_id: str, value) -> None:
        """
        Set the raw value of a node (DISABLE or ADJUSTABLE) and return its refreshed IndexEntry.
        Raises TypeError if the node is not found or if there's a type mismatch.
        """
        # Try adjustable first, then disableable
        try:
            self._set_value(self._assembled.adjustable_nodes, widget_group, widget_id, value)
        except NodeNotFound:
            self._set_value(self._assembled.disableable_nodes, widget_group, widget_id, value)
        
    def get_value(self, widget_group: str, widget_id: str):
        """
        Get the current raw value of a node (DISABLE or ADJUSTABLE).
        Raises TypeError if the node is not found or if there's a type mismatch.
        """
        try:
            return self._get_value(self._assembled.adjustable_nodes, widget_group, widget_id)
        except NodeNotFound:
            return self._get_value(self._assembled.disableable_nodes, widget_group, widget_id)
        
    # ------------------------------------------------------------------ #
    # Public API — tree views                                              #
    # ------------------------------------------------------------------ #

    def get_values(self) -> dict[str, dict[str, tuple]]:
        """
        Return the current value and enabled state for every node in the
        configuration.
        """
        result = {}
        if self._assembled is None:
            return result
        for group_label, group in self._assembled.all_nodes.items():
            result[group_label] = {}
            for widget_id, node_status in group.items():
                result[group_label][widget_id] = (node_status.node.get(), node_status.is_enabled, node_status.is_interactive)
        return result  

    def get_tree_views(self) -> TreeViews:
        """
        { view_panel: Rich Tree, ... }
        Only populated for AssembledGroups where view_panel != "".
        Returns empty dict if no config is loaded.
        """
        return self._tree_views or {}

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_tree_views(assembled: AssembledConfig) -> TreeViews:
        """
        Build a Rich Tree for every disableable group that has a view_panel label.
        Each system root in the group becomes a subtree. Called on every
        refresh_information() since trees are rendered snapshots of live state.
        """
        views: TreeViews = {}
        for group in assembled.disableable:
            if not group.view_panel:
                continue
            panel_tree = Tree(group.view_panel)
            for system in group.systems:
                panel_tree.children.append(
                    draw_tree(system.root.label, system.root)
                )
            views[group.view_panel] = panel_tree
        return views