import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from conffwk import Configuration
from rich.tree import Tree

from runconf_ui.exceptions import NodeNotFound, RunConfToolsRepoException
from runconf_ui.repo_manager import LocalRepoManager, RemoteRepoManager
from runconf_ui.state_tree import NodeStatus, walk
from runconf_ui.system_configuration import SystemConfigReader
from runconf_ui.system_configuration.config_reader import AssembledConfig
from runconf_ui.utils import copy_and_open_config
from runconf_ui.utils.rich_utils import ConfigTreeRenderer, draw_node_tree


@dataclass
class RunconfContext:
    apparatus: str
    conf_directory: Path
    use_local: bool
    config_file_name: str | None = None
    base_url: str | None = None
    ops_url: str | None = None
    output_directory: Path = Path("shifter-configs")

TreeViews = dict[str, Tree]


class RunconfUIBackend:
    def __init__(self, context: RunconfContext):
        if context.use_local:
            self.repo_manager = LocalRepoManager(context.apparatus, context.conf_directory)
        else:
            if any(v is None for v in (context.config_file_name, context.base_url, context.ops_url)):
                raise RunConfToolsRepoException(
                    "Must set default_config, base_url, and ops_url for remote use"
                )
            self.repo_manager = RemoteRepoManager(
                context.apparatus, context.conf_directory,
                context.config_file_name, context.ops_url, context.base_url,
            )

        buffer_id = os.environ.get("SESSION_NAME", os.getlogin())
        self._config_buffer_path = Path(f"/tmp/shifter_configs-{buffer_id}")
        self._save_path = context.output_directory/f"{context.apparatus}.data.xml"

        self.apparatus = context.apparatus

        self._assembled: AssembledConfig | None = None
        self._tree_views: TreeViews = {}
        self.system_config_reader: SystemConfigReader | None = None
        self._selected_session: str | Path | None = None
        
        self.configuration: Configuration|None = None
        self.config_tree_renderer=None
        self.config_session=None
        
        self.info_text="No Config Selected"

    # ------------------------------------------------------------------ #
    # Setup                                                                #
    # ------------------------------------------------------------------ #
    def get_daq_versions(self):
        return self.repo_manager.get_available_daq_versions()
    
    def get_current_version(self):
        return self.repo_manager.daq_version

    def get_sessions(self):
        return self.repo_manager.get_daq_sessions()

    def get_current_session(self):
        return self._selected_session
    
    def set_daq_version(self, version) -> None:
        self.repo_manager.set_daq_version(version)

    def set_daq_session(self, session: str | Path | None) -> None:
        self._selected_session = session

    def open_selected_session(self) -> None:
        if self.repo_manager.get_runconf_ui_config_path() is None:
            raise RunConfToolsRepoException("Select a DAQ version before selecting a session")

        if self._selected_session is None:
            raise RunConfToolsRepoException("No session selected!")

        if self._selected_session not in self.get_sessions():
            raise RunConfToolsRepoException(f"Cannot find session {self._selected_session}")

        self.system_config_reader = SystemConfigReader(
            self.repo_manager.get_runconf_ui_config_path()
        )

        init_config_path = self.repo_manager.select_config(self._selected_session)

        tmp_config_path = self._config_buffer_path / f"cfg_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.data.xml"
        self.configuration = copy_and_open_config(init_config_path, tmp_config_path)

        self.config_session = self.configuration.get_dals('Session')[0]

        self.config_tree_renderer = ConfigTreeRenderer(self.configuration,
                                                       self.config_session,
                                                       self.system_config_reader.classes_to_draw)

        self._assembled = self.system_config_reader.assemble_config(
            self.configuration, self.config_session.id
        )
        self.update_info_text(init_config_path)
        self._rebuild_indexes()
        
    def update_info_text(self, init_config_path):
    
        self.info_text= (f"      [bold green]DAQ Version[/bold green]:  [deep_pink4]{self.get_current_version()}[/deep_pink4]\n"
                         f"      [bold green]Apparatus[/bold green]:  [deep_pink4]{self.apparatus}[/deep_pink4]\n"
                         f"      [bold green]DAQ Config[/bold green]: [deep_pink4]{init_config_path}[/deep_pink4]\n"
                         f"      [bold green]Current Config File[/bold green]:  [deep_pink4]{self.configuration.active_database}[/deep_pink4]\n"
                         f"      [bold green]Session in Config[/bold green]:  [deep_pink4]{self.config_session.id}\n")

    def save_config(self):
        '''Save configuration to buffer file then copy the config to the save path.'''
        if self.configuration is None:
            raise FileExistsError("Configuration file not found!")
        self.configuration.commit()
        
        self._save_path.parent.mkdir(parents=True, exist_ok=True)
        config_path = Path(self.configuration.active_database)
        
        copy_and_open_config(config_path, self._save_path)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #
    def get_value(self, group: str, node_id: str):
        return self._resolve(group, node_id).node.get()

    def set_value(self, group: str, node_id: str, value) -> None:
        self._resolve(group, node_id).node.set(value)
        self._rebuild_indexes()

    def toggle(self, group: str, node_id: str) -> None:
        self._resolve(group, node_id, collection="disableable").toggle()
        self._rebuild_indexes()

    def get_values(self) -> dict[str, dict[str, NodeStatus]]:
        '''Returns all nodes (adjustable + disableable).'''
        if self._assembled is None:
            return {}
        return {
            group_label: dict(nodes)
            for group_label, nodes in self._assembled.all_nodes.items()
        }

    def get_disableable_values(self) -> dict[str, dict[str, NodeStatus]]:
        '''Returns only disableable nodes — used by the controls panel.'''
        if self._assembled is None:
            return {}
        return {
            group_label: dict(nodes)
            for group_label, nodes in self._assembled.disableable_nodes.items()
        }

    def get_adjustable_values(self) -> dict[str, dict[str, NodeStatus]]:
        '''Returns only adjustable nodes.'''
        if self._assembled is None:
            return {}
        return {
            group_label: dict(nodes)
            for group_label, nodes in self._assembled.adjustable_nodes.items()
        }

    def get_tree_views(self) -> TreeViews:
        return self._tree_views

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _resolve(self, group: str, node_id: str, collection: str = "all") -> NodeStatus:
        if self._assembled is None:
            raise NodeNotFound("No configuration loaded")

        index = {
            "all": self._assembled.all_nodes,
            "disableable": self._assembled.disableable_nodes,
            "adjustable": self._assembled.adjustable_nodes,
        }[collection]

        nodes = index.get(group)
        if nodes is None:
            raise NodeNotFound(f"Group {group!r} not found. Available: {list(index)}")

        node = nodes.get(node_id)
        if node is None:
            raise NodeNotFound(f"Node {node_id!r} not found in group {group!r}. Available: {list(nodes)}")

        return node

    def _rebuild_indexes(self) -> None:
        a = self._assembled
        if a is None:
            return

        for group in (*a.disableable, *a.adjustable):
            group.nodes = {}
            for system in group.systems:
                system.nodes = {s.path: s for s in walk(system.root) if s.path is not None
                                and (system.display_full_system or s.parent is not None)
                                }
                group.nodes.update(system.nodes)

        a.disableable_nodes = {g.id: g.nodes for g in a.disableable}
        a.adjustable_nodes  = {g.id: g.nodes for g in a.adjustable}
        a.all_nodes = {**a.adjustable_nodes, **a.disableable_nodes}

        # Key by group.id (clean string) rather than group.view_panel (may contain spaces)
        self._tree_views = {
            group.id: self._build_panel_tree(group)
            for group in a.disableable
            if group.view_panel
        }

    @staticmethod
    def _build_panel_tree(group) -> Tree:
        tree = Tree(group.view_panel)
        for system in group.systems:
            tree.children.append(draw_node_tree(system.root.label, system.root))
        return tree
    
    def get_config_tree(self)->Tree:
        if self.config_tree_renderer is None:
            return Tree("No Config Loaded")
        
        return self.config_tree_renderer.draw_config_tree()