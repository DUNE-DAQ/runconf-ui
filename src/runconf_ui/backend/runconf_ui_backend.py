import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TextIO

from conffwk import Configuration
from conffwk.dal import DalBase
from rich import print as rprint
from rich.tree import Tree

from runconf_ui.exceptions import NodeNotFound, RunConfToolsRepoException
from runconf_ui.repo_manager import RepoManagerInterface, repo_factory
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
    """Context required to initialise the runconf-ui backend
    :param apparatus: str name of the apparatus to load configs for (np02/np04/etc.)
    :param conf_directory: path to the config repository (local or remote)
    :param use_local: whether to use the local filesystem or remote API to load configs
    :param config_file_name: (remote only) the default config file to load when apparatus is selected. This should be a file that exists in the remote repository and contains a session that matches the apparatus name.
    :param base_url: (remote only) URL for the BASE repository, used to populate the dropdown for config selection and load the default config.
    :param ops_url: (remote only) URL for the operations repository, used to populate the dropdown for config selection and load the default config.
    :param output_directory: directory to save configs to when the user clicks "Save".
    :param log_level: log level for the backend logger (default: INFO)
    """

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

    repo_manager: RepoManagerInterface

    def __init__(self, context: RunconfContext):
        """Session management

        :param context: Runconf context
        :raises RunConfToolsRepoException: The default config has not been set (Remote only)
        :raises RunConfToolsRepoException: The base_url has not been set (Remote only)
        :raises RunConfToolsRepoException: The ops_url has not been set (Remote only)
        """
        self._logger = get_logger()

        self.repo_manager = repo_factory(
            apparatus=context.apparatus,
            conf_directory=context.conf_directory,
            use_local=context.use_local,
            config_file_name=context.config_file_name,
            ops_url=context.ops_url,
            base_url=context.base_url,
        )

        try:
            backup = os.getlogin()
        except OSError:
            backup = "unknown_user"

        buffer_id = os.environ.get("SESSION_NAME", backup)
        self._logger.debug(f"Buffer ID is {buffer_id}")

        self._config_buffer_path = Path(f"/tmp/shifter_configs-{buffer_id}")
        self._logger.debug(f"Saving configs to  {self._config_buffer_path}")

        self._selected_session: str | Path | None = None

    # ---- Version / session selection ----

    def get_daq_versions(self):
        """Get the available DAQ versions from the repository manager."""
        return self.repo_manager.get_available_daq_versions()

    def get_current_version(self):
        """Get the currently selected DAQ version from the repository manager."""
        return self.repo_manager.daq_version

    def get_sessions(self):
        """Get the available sessions for the currently selected DAQ version from the repository manager."""
        return self.repo_manager.get_daq_sessions()

    def get_current_session(self):
        """Get the currently selected session."""
        return self._selected_session

    def set_daq_version(self, version) -> None:
        """Set the DAQ version in the repository manager, which will update the available sessions."""
        self.repo_manager.set_daq_version(version)

    def set_daq_session(self, session: str | Path | None) -> None:
        """Set the selected session."""
        self._selected_session = session

    def get_runconf_ui_config_path(self):
        """Get the path to the currently selected RUNCONF-UI config file from the repository manager."""
        return self.repo_manager.get_runconf_ui_config_path()

    def get_default_version(self) -> str:
        """Get the default DAQ version"""
        return self.repo_manager.default_version

    # ---- Config loading ----

    def load_session(self) -> tuple[Configuration, DalBase, Path]:
        """
        Validate the current selection, buffer a copy of the config, and
        return (configuration, config_session dal, original_config_path).

        :returns: Tuple of (Configuration, config session DAL, original config path)
        :raises RunConfToolsRepoException: No session selected
        :raises RunConfToolsRepoException: Selected session not found in available sessions
        :raises RunConfToolsRepoException: Config session not found in loaded configuration

        """

        if self._selected_session is None:
            raise RunConfToolsRepoException("No session selected!")

        if self._selected_session not in self.get_sessions():
            raise RunConfToolsRepoException(
                f"Cannot find session {self._selected_session} in {self.get_sessions()}"
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
    """Full backend interface for the runconf-ui logical components.

    This class manages session/version selection, config lifecycle, state queries,
    and interactions with the configuration framework.
    """

    def __init__(self, context: RunconfContext):
        """
        Full backend interface for the logical components of the interface
        :param context: RunconfContext object containing necessary information to initialise the backend.
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
    # Session / version forwarding [I hate this]                         #
    # ------------------------------------------------------------------ #

    def get_daq_versions(self):
        """Forward the request for available DAQ versions to the session manager."""
        return self._session_manager.get_daq_versions()

    def get_default_version(self):
        """Forward the request for default DAQ version to the session manager."""
        return self._session_manager.get_default_version()

    def get_current_version(self):
        """Forward the request for the current DAQ version to the session manager."""
        return self._session_manager.get_current_version()

    def get_sessions(self):
        """Forward the request for available sessions to the session manager."""
        return self._session_manager.get_sessions()

    def get_current_session(self):
        """Forward the request for the current session to the session manager."""
        return self._session_manager.get_current_session()

    def set_daq_version(self, version) -> None:
        """Forward the request to set the DAQ version to the session manager.
        :param version: the DAQ version to set, e.g. "v3.0.0"
        """
        self._session_manager.set_daq_version(version)

    def set_daq_session(self, session: str | Path | None) -> None:
        """Forward the request to set the DAQ session to the session manager.
        :param session: the DAQ session to set i.e. "CRT"
        """
        self._session_manager.set_daq_session(session)

    # ------------------------------------------------------------------ #
    # Config lifecycle                                                     #
    # ------------------------------------------------------------------ #
    def open_selected_session(self) -> None:
        """Open the selected DAQ session

        :raises RunConfToolsRepoException: Session's not been found in the repository manager
        """
        self._logger.debug("Opening session")
        self._logger.debug("Loading session")
        self.configuration, self.config_session, init_config_path = (
            self._session_manager.load_session()
        )

        self.system_config_reader = SystemConfigReader(
            self._session_manager.get_runconf_ui_config_path()
        )

        if self.config_session is None:
            self._logger.error("Config session not found in configuration")
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
        """Get the path where the config will be saved.

        :returns: Path object representing the config save location
        :rtype: Path
        """
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
        """Retrieve the value of a configuration node.

        :param group: The configuration group name
        :param node_id: The unique identifier of the node
        :returns: The current value of the specified node
        :raises NodeNotFound: If the group or node is not found
        """
        return self._resolve(group, node_id).node.get()

    def set_value(self, group: str, node_id: str, value) -> None:
        """Set the value of a configuration node.

        :param group: The configuration group name
        :param node_id: The unique identifier of the node
        :param value: The new value to set
        :raises NodeNotFound: If the group or node is not found
        """
        self._resolve(group, node_id).node.set(value)
        self._rebuild_indexes()

    def toggle(self, group: str, node_id: str) -> None:
        """Toggle the enabled/disabled state of a configuration node.

        :param group: The configuration group name
        :param node_id: The unique identifier of the node
        :raises NodeNotFound: If the group or node is not found
        """
        self._resolve(group, node_id, collection="disableable").toggle()
        self._rebuild_indexes()

    def get_values(self) -> dict[str, dict[str, NodeStatus]]:
        """Retrieve all configuration node values organized by group.

        :returns: Dictionary mapping group names to node status dictionaries
        :rtype: dict[str, dict[str, NodeStatus]]
        """
        if self._assembled is None:
            return {}
        return {g: dict(n) for g, n in self._assembled.all_nodes.items()}

    def get_disableable_values(self) -> dict[str, dict[str, NodeStatus]]:
        """Retrieve all disableable configuration nodes organized by group.

        :returns: Dictionary mapping group names to disableable node status dictionaries
        :rtype: dict[str, dict[str, NodeStatus]]
        """
        if self._assembled is None:
            return {}
        return {g: dict(n) for g, n in self._assembled.disableable_nodes.items()}

    def get_adjustable_values(self) -> dict[str, dict[str, NodeStatus]]:
        """Retrieve all adjustable configuration nodes organized by group.

        :returns: Dictionary mapping group names to adjustable node status dictionaries
        :rtype: dict[str, dict[str, NodeStatus]]
        """
        if self._assembled is None:
            return {}
        return {g: dict(n) for g, n in self._assembled.adjustable_nodes.items()}

    def get_tree_views(self) -> TreeViews:
        """Retrieve all available tree view representations.

        :returns: Dictionary mapping panel identifiers to Tree views
        :rtype: TreeViews
        """
        return self._tree_views

    def get_config_tree(self) -> Tree:
        """Get the current configuration tree representation.

        :returns: Rich Tree object representing the configuration structure
        :rtype: Tree
        """
        if self.config_tree_renderer is None:
            return Tree("No Config Loaded")
        return self.config_tree_renderer.draw_config_tree()

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _update_info_text(self, init_config_path: Path) -> None:
        """Update the information text with current configuration details.

        :param init_config_path: Path to the initial configuration file
        """
        self.info_text = (
            f"      [bold green]DAQ Version[/bold green]:  [deep_pink4]{self.get_current_version()}[/deep_pink4]\n"
            f"      [bold green]Apparatus[/bold green]:  [deep_pink4]{self.apparatus}[/deep_pink4]\n"
            f"      [bold green]DAQ Config[/bold green]: [deep_pink4]{init_config_path}[/deep_pink4]\n"
            f"      [bold green]Current Config File[/bold green]:  [deep_pink4]{self.configuration.active_database if self.configuration else None}[/deep_pink4]\n"
            f"      [bold green]Session in Config[/bold green]:  [deep_pink4]{self.config_session.id if self.config_session else None}[/deep_pink4]\n"
        )

    def _resolve(self, group: str, node_id: str, collection: str = "all") -> NodeStatus:
        """Resolve a configuration node from the specified collection.

        :param group: The configuration group name
        :param node_id: The unique identifier of the node
        :param collection: The collection to search from ('all', 'disableable', 'adjustable')
        :returns: The NodeStatus object containing the resolved node
        :rtype: NodeStatus
        :raises NodeNotFound: If the group or node is not found
        """
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
        """Rebuild the node indices for all groups and systems in parallel.

        Dispatches each group's walk() traversal to a worker thread.
        walk() is a pure read over an independent subtree, so concurrent
        execution is safe.  Results are collected and merged on the main
        thread before updating the assembled config dictionaries.
        """
        self._logger.debug("Rebuilding indices")
        a = self._assembled
        if a is None:
            return

        all_groups = [*a.disableable, *a.adjustable]

        if not all_groups:
            return

        def _rebuild_group(group) -> tuple:
            """Rebuild a single group's node index.

            :returns: (group, nodes_dict) tuple
            """
            group.nodes = {}
            for system in group.systems:
                system.nodes = {
                    s.path: s
                    for s in walk(system.root)
                    if s.path is not None
                    and (system.display_full_system or s.parent is not None)
                }
                group.nodes.update(system.nodes)
            return group, group.nodes

        max_workers = min(32, len(all_groups))
        self._logger.debug(
            f"Rebuilding {len(all_groups)} group index(es) "
            f"with up to {max_workers} worker thread(s)"
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_rebuild_group, g): g for g in all_groups}
            for future in as_completed(futures):
                future.result()  # re-raise any exception from the thread

        # Sort and publish — done on the main thread after all walks complete
        a.disableable_nodes = {g.id: a._sorted_nodes(g.nodes) for g in a.disableable}
        a.adjustable_nodes = {g.id: a._sorted_nodes(g.nodes) for g in a.adjustable}
        a.all_nodes = {**a.adjustable_nodes, **a.disableable_nodes}

        self._tree_views = {
            group.id: self._build_panel_tree(group)
            for group in a.disableable + a.adjustable
            if group.view_panel
        }

    @staticmethod
    def _build_panel_tree(group) -> Tree:
        """Build a tree representation for a configuration group.

        :param group: The configuration group to render
        :returns: Rich Tree object representing the group structure
        :rtype: Tree
        """
        tree = Tree(group.view_panel)
        for system in group.systems:
            tree.children.append(draw_node_tree(system.root.label, system.root))
        return tree

    def print_trees_to_file(self, text_file: TextIO) -> None:
        """Print all tree views to a text file.

        :param text_file: An open text file object to write the trees to
        :type text_file: TextIO
        """
        section_marker = "==============================\n"

        rprint("## Main Tree ##\n")
        rprint(self.get_config_tree(), file=text_file)
        rprint(section_marker, file=text_file)

        for lab, tr in self.get_tree_views().items():
            rprint(f"## {lab} ##\n", file=text_file)
            rprint(tr, file=text_file)
            rprint(section_marker, file=text_file)
