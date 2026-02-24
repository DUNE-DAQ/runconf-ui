'''
Wraps around runconf-ui, this "hides" most of the implementation details and handles the operations
required for file loading/opening
'''
from pathlib import Path
from dataclasses import dataclass

from rich.tree import Tree

from runconf_ui.exceptions import RunConfToolsRepoException
from runconf_ui.repo_manager import LocalRepoManager, RemoteRepoManager
from runconf_ui.system_configuration import SystemConfigReader
from runconf_ui.system_configuration.config_reader import AssembledConfig
from runconf_ui.utils import open_configuration
from runconf_ui.utils.rich_utils import draw_tree

from .node_index import (
    IndexEntry,
    GroupedIndex,
    NodeIndex,
    NodeKind,
    build_disable_index,
    build_adjustable_index,
    build_node_index,
    get_value,
    set_value,
    toggle_node,
)


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

        # Structural indexes — built once on load, never rebuilt
        self._node_index: NodeIndex | None = None
        self._disable_index: GroupedIndex | None = None
        self._adjustable_index: GroupedIndex | None = None

        # Tree views — rebuilt on every refresh_information()
        self._tree_views: TreeViews | None = None

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
            self._node_index = None
            self._disable_index = None
            self._adjustable_index = None
            self._tree_views = None

    def select_config(self, config):
        if self.system_config_reader is None:
            raise RunConfToolsRepoException("No DAQ configuration setup, please select version first")

        self.configuration = open_configuration(self.repo_manager.select_config(config))

        self._assembled = self.system_config_reader.assemble_config(
            self.configuration,
            self.configuration.get_dals('Session')[0].id
        )

        # Build structural indexes once
        self._disable_index    = build_disable_index(self._assembled)
        self._adjustable_index = build_adjustable_index(self._assembled)
        self._node_index       = build_node_index(self._assembled)

        # Build initial tree views
        self.refresh_information()

    # ------------------------------------------------------------------ #
    # Refresh                                                              #
    # ------------------------------------------------------------------ #

    def refresh_information(self) -> None:
        """
        Recompute tree views from live adapter state.

        Called after any toggle; the TUI app should then post RunconfRefreshed
        so all subscribed widgets resync. Returns immediately if no config
        is loaded — widgets will render from empty state.
        """
        if self._assembled is None:
            return
        self._tree_views = self._build_tree_views(self._assembled)

    # ------------------------------------------------------------------ #
    # Public API — disable                                                 #
    # ------------------------------------------------------------------ #

    def get_disable_index(self) -> GroupedIndex:
        """
        { group_label: { widget_id: IndexEntry, ... }, ... }
        Only DISABLE nodes. Returns empty dict if no config is loaded.
        """
        return self._disable_index or {}

    def toggle(self, widget_id: str) -> IndexEntry:
        """
        Toggle a DISABLE node and return its refreshed IndexEntry.
        Raises TypeError if called on an ADJUSTABLE node.
        """
        if self._node_index is None:
            raise RunConfToolsRepoException("No configuration loaded")
        return toggle_node(self._node_index, widget_id)

    # ------------------------------------------------------------------ #
    # Public API — adjustable                                              #
    # ------------------------------------------------------------------ #

    def get_adjustable_index(self) -> GroupedIndex:
        """
        { group_label: { widget_id: IndexEntry, ... }, ... }
        Only ADJUSTABLE nodes. Returns empty dict if no config is loaded.
        """
        return self._adjustable_index or {}

    def get_value(self, widget_id: str):
        """
        Get the current raw value of an ADJUSTABLE node.
        Raises TypeError if called on a DISABLE node.
        """
        if self._node_index is None:
            raise RunConfToolsRepoException("No configuration loaded")
        return get_value(self._node_index, widget_id)

    def set_value(self, widget_id: str, value) -> IndexEntry:
        """
        Set the raw value of an ADJUSTABLE node and return its refreshed IndexEntry.
        Raises TypeError if called on a DISABLE node.
        """
        if self._node_index is None:
            raise RunConfToolsRepoException("No configuration loaded")
        return set_value(self._node_index, widget_id, value)

    # ------------------------------------------------------------------ #
    # Public API — tree views                                              #
    # ------------------------------------------------------------------ #

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