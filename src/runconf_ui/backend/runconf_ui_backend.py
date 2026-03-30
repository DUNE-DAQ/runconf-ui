import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TextIO

from conffwk import Configuration
from conffwk.dal import DalBase
from rich import print as rprint
from rich.tree import Tree

from runconf_ui.exceptions import NodeNotFound, RunConfToolsRepoException
from runconf_ui.repo_manager import LocalRepoManager, RemoteRepoManager
from runconf_ui.state_tree import NodeStatus, walk
from runconf_ui.system_configuration import SystemConfigReader
from runconf_ui.system_configuration.config_reader import AssembledConfig
from runconf_ui.utils import (
    LogLevels,
    copy_and_open_config,
    get_logger,
    init_logger,
    setup_working_directory,
)
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
    log_level: LogLevels = "INFO"


TreeViews = dict[str, Tree]


# ---------------------------------------------------------------------------
# Session management — versioning, session selection, loading
# ---------------------------------------------------------------------------


class _SessionManager:
    """Owns repo interaction and config loading. No state querying here."""

    repo_manager: LocalRepoManager | RemoteRepoManager

    def __init__(self, context: RunconfContext):
        self._logger = get_logger()

        if context.use_local:
            self._logger.debug("Using local repo manager")
            self.repo_manager = LocalRepoManager(
                context.apparatus, context.conf_directory
            )
        else:
            if context.config_file_name is None:
                raise RunConfToolsRepoException(
                    "Must set default_config for remote use"
                )
            if context.base_url is None:
                raise RunConfToolsRepoException("Must set base_url for remote use")
            if context.ops_url is None:
                raise RunConfToolsRepoException("Must set ops_url for remote use")

            self._logger.debug("Using remote repo manager")
            self.repo_manager = RemoteRepoManager(
                context.apparatus,
                context.conf_directory,
                context.config_file_name,
                context.ops_url,
                context.base_url,
            )

        buffer_id = os.environ.get("SESSION_NAME", os.getlogin())
        self._logger.debug(f"Buffer ID is {buffer_id}")

        self._config_buffer_path = Path(f"/tmp/shifter_configs-{buffer_id}")
        self._logger.debug(f"Saving configs to  {self._config_buffer_path}")

        self._selected_session: str | Path | None = None

    # ---- Version / session selection ----

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

    def get_runconf_ui_config_path(self):
        return self.repo_manager.get_runconf_ui_config_path()

    # ---- Config loading ----

    def load_session(self) -> tuple[Configuration, DalBase, Path]:
        """
        Validate the current selection, buffer a copy of the config, and
        return (configuration, config_session dal, original_config_path).
        """

        if self._selected_session is None:
            raise RunConfToolsRepoException("No session selected!")

        if self._selected_session not in self.get_sessions():
            raise RunConfToolsRepoException(
                f"Cannot find session {self._selected_session}"
            )

        init_config_path = self.repo_manager.select_config(self._selected_session)  # type: ignore

        tmp_path = (
            self._config_buffer_path
            / f"cfg_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.data.xml"
        )
        configuration = copy_and_open_config(init_config_path, tmp_path)

        config_session = configuration.get_dals("Session")[0]

        if self.repo_manager.get_runconf_ui_config_path() is None:
            raise RunConfToolsRepoException(
                "Select a DAQ version before selecting a session"
            )

        self._logger.info(
            f"Loaded configuration from {init_config_path} -> {tmp_path}. With session {config_session.id}"
        )

        return configuration, config_session, init_config_path


# ---------------------------------------------------------------------------
# RunconfUIBackend — public API used by the TUI layer
# ---------------------------------------------------------------------------


class RunconfUIBackend:
    def __init__(self, context: RunconfContext):
        """
        Full backend interface for the logical components of the interface
        """

        # Set up logging and save path
        creation_time = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

        self.final_save_dir, self.current_save_dir = setup_working_directory(
            context.output_directory, creation_time
        )

        log_path = self.current_save_dir / f"{context.apparatus}_{creation_time}.log"
        init_logger(log_path, context.log_level)
        self._save_path = (
            self.current_save_dir / f"{context.apparatus}_{creation_time}.data.xml"
        )

        self._logger = get_logger()

        self._session_manager = _SessionManager(context)
        self.apparatus = context.apparatus

        self._assembled: AssembledConfig | None = None
        self._tree_views: TreeViews = {}
        self.system_config_reader: SystemConfigReader | None = None

        self.configuration: Configuration | None = None
        self.config_tree_renderer = None
        self.config_session = None
        self.info_text = "No Config Selected"

        self._logger.debug("Backend instantiated")

    # ------------------------------------------------------------------ #
    # Session / version forwarding                                         #
    # ------------------------------------------------------------------ #

    def get_daq_versions(self):
        return self._session_manager.get_daq_versions()

    def get_current_version(self):
        return self._session_manager.get_current_version()

    def get_sessions(self):
        return self._session_manager.get_sessions()

    def get_current_session(self):
        return self._session_manager.get_current_session()

    def set_daq_version(self, version) -> None:
        self._session_manager.set_daq_version(version)

    def set_daq_session(self, session: str | Path | None) -> None:
        self._session_manager.set_daq_session(session)

    # ------------------------------------------------------------------ #
    # Config lifecycle                                                     #
    # ------------------------------------------------------------------ #
    def open_selected_session(self) -> None:
        self._logger.debug("Opening session")
        self.system_config_reader = SystemConfigReader(
            self._session_manager.get_runconf_ui_config_path()
        )
        self._logger.debug("Loading session")
        self.configuration, self.config_session, init_config_path = (
            self._session_manager.load_session()
        )

        if self.config_session is None:
            raise RunConfToolsRepoException("Config session not found in configuration")

        self._logger.debug("Rendering trees")
        self.config_tree_renderer = ConfigTreeRenderer(
            self.configuration,
            self.config_session,
            self.system_config_reader.classes_to_draw,
        )

        self._logger.debug("Assembling config")
        self._assembled = self.system_config_reader.assemble_config(
            self.configuration, self.config_session.id
        )
        self._update_info_text(init_config_path)
        self._logger.debug("Rebuilding indices")

        self._rebuild_indexes()
        self._logger.debug("Loaded")

    @property
    def config_save_path(self) -> Path:
        return self.current_save_dir / self._save_path.name

    def save_config(self) -> None:
        """
        Commit the in-memory config then write a consolidated copy to the
        save path. copy_and_open_config is used for its consolidation side
        effect; the returned Configuration object is not needed here.
        """

        self._logger.info(f"Saving config to {self.current_save_dir}")
        if self.configuration is None:
            raise FileExistsError("Configuration file not found!")
        self.configuration.commit()
        self._save_path.parent.mkdir(parents=True, exist_ok=True)
        copy_and_open_config(Path(self.configuration.active_database), self._save_path)

        # Save the trees as well
        with open(self.current_save_dir / "detector_status.txt", "w") as f:
            self.print_trees_to_file(f)

        # Copy everything to the correct directory
        shutil.rmtree(self.final_save_dir)
        shutil.copytree(self.current_save_dir, self.final_save_dir, dirs_exist_ok=True)

        self._logger.info(f"Saved config to {self.current_save_dir}")

    # ------------------------------------------------------------------ #
    # State queries                                                        #
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
        if self._assembled is None:
            return {}
        return {g: dict(n) for g, n in self._assembled.all_nodes.items()}

    def get_disableable_values(self) -> dict[str, dict[str, NodeStatus]]:
        if self._assembled is None:
            return {}
        return {g: dict(n) for g, n in self._assembled.disableable_nodes.items()}

    def get_adjustable_values(self) -> dict[str, dict[str, NodeStatus]]:
        if self._assembled is None:
            return {}
        return {g: dict(n) for g, n in self._assembled.adjustable_nodes.items()}

    def get_tree_views(self) -> TreeViews:
        return self._tree_views

    def get_config_tree(self) -> Tree:
        if self.config_tree_renderer is None:
            return Tree("No Config Loaded")
        return self.config_tree_renderer.draw_config_tree()

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _update_info_text(self, init_config_path: Path) -> None:
        self.info_text = (
            f"      [bold green]DAQ Version[/bold green]:  [deep_pink4]{self.get_current_version()}[/deep_pink4]\n"
            f"      [bold green]Apparatus[/bold green]:  [deep_pink4]{self.apparatus}[/deep_pink4]\n"
            f"      [bold green]DAQ Config[/bold green]: [deep_pink4]{init_config_path}[/deep_pink4]\n"
            f"      [bold green]Current Config File[/bold green]:  [deep_pink4]{self.configuration.active_database if self.configuration else None}[/deep_pink4]\n"
            f"      [bold green]Session in Config[/bold green]:  [deep_pink4]{self.config_session.id if self.config_session else None}[/deep_pink4]\n"
        )

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
            raise NodeNotFound(
                f"Node {node_id!r} not found in group {group!r}. Available: {list(nodes)}"
            )

        return node

    def _rebuild_indexes(self) -> None:
        self._logger.debug("Rebuilding indices")
        a = self._assembled
        if a is None:
            return

        for group in (*a.disableable, *a.adjustable):
            group.nodes = {}
            self._logger.debug(f"Building nodes for {group}")

            for system in group.systems:
                self._logger.debug(f"   Building nodes for system: {system}")
                system.nodes = {
                    s.path: s
                    for s in walk(system.root)
                    if s.path is not None
                    and (system.display_full_system or s.parent is not None)
                }
                group.nodes.update(system.nodes)

        a.disableable_nodes = {g.id: a._sorted_nodes(g.nodes) for g in a.disableable}
        a.adjustable_nodes = {g.id: a._sorted_nodes(g.nodes) for g in a.adjustable}
        a.all_nodes = {**a.adjustable_nodes, **a.disableable_nodes}

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

    def print_trees_to_file(self, text_file: TextIO):
        section_marker = "==============================\n"

        rprint("## Main Tree ##\n")
        rprint(self.get_config_tree(), file=text_file)
        rprint(section_marker, file=text_file)

        for lab, tr in self.get_tree_views().items():
            rprint(f"## {lab} ##\n", file=text_file)
            rprint(tr, file=text_file)
            rprint(section_marker, file=text_file)
