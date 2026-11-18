"""
gRPC service exposing RunconfUIBackend via the runconfschema protobufs.
"""

from __future__ import annotations

import functools
import threading
from concurrent import futures
from pathlib import Path
from typing import Any

import grpc
from google.protobuf.wrappers_pb2 import StringValue
from rich.text import Text
from rich.tree import Tree
from runconfschema import runconf_services_pb2_grpc
from runconfschema.bootstrap_pb2 import BootRequest
from runconfschema.common_pb2 import Error, OutcomeFlag, Response
from runconfschema.configuration_access_pb2 import (
    ConfigurationOutcome,
    DropDownContent,
    DropDownSelection,
    DropDownUpdate,
    Initialisation,
    Open,
)
from runconfschema.display_pb2 import DisplayTree, DisplayViews, GroupTree, RequestViews
from runconfschema.main_controls_pb2 import (
    RunconfCommand,
    RunconfCommandRequest,
    RunconfCommandResponse,
)
from runconfschema.state_pb2 import (
    NodeGroup,
    NodeStatusInfo,
    RequestNodeStatus,
    RequestReset,
    RequestSetNodeValue,
    ResponseNodeStatus,
)
from runconfschema.state_pb2 import NodeStatus as NodeStatusRpc

from runconf_ui.backend import RunconfContext, RunconfUIBackend
from runconf_ui.exceptions import _RunconfUIException
from runconf_ui.repo_manager import RepoManagerType
from runconf_ui.state_tree import NodeStatus, State

# Exceptions we turn into a FAIL Response rather than a gRPC error.
_EXPECTED_ERRORS = (_RunconfUIException, KeyError, ValueError, OSError)

PathKey = tuple[str, ...]

# ---------------------------------------------------------------------------
# Conversions
# ---------------------------------------------------------------------------

_STATE_TO_RPC = {
    State.INCLUDED: NodeStatusRpc.INCLUDED,
    State.EXCLUDED: NodeStatusRpc.EXCLUDED,
    State.PARENT_EXCLUDED: NodeStatusRpc.PARENT_EXCLUDED,
}


def ok(message: str) -> Response:
    return Response(outcome=OutcomeFlag.SUCCESS, message=message)


def fail(message: str, exc: Exception | None = None) -> Response:
    r = Response(outcome=OutcomeFlag.FAIL, message=message)
    if exc is not None:
        r.error.CopyFrom(Error(message=str(exc)))
    return r


def set_typed_value(info: NodeStatusInfo, value: Any) -> None:
    """Fill the NodeStatusInfo.value oneof from a python value (None -> unset)."""
    if value is None:
        return
    if isinstance(value, bool):  # before int: bool is an int subclass
        info.bool_value = value
    elif isinstance(value, int):
        info.int_value = value
    elif isinstance(value, float):
        info.double_value = value
    else:
        info.string_value = str(value)


def node_to_rpc(group_id: str, status: NodeStatus, node_group: int) -> NodeStatusInfo:
    """Backend NodeStatus -> NodeStatusInfo. Path is [group_id, *status.path parts]."""
    info = NodeStatusInfo(
        node_state=_STATE_TO_RPC[status.state],
        node_path=[group_id, *(status.path or "").split("__")],
        tooltip=status.node.tooltip,
        node_group=node_group,
    )
    set_typed_value(info, status.node.get())
    return info


def tree_to_rpc(tree: Tree) -> DisplayTree:
    """Rich Tree -> DisplayTree. Labels are kept as Rich markup."""
    label = tree.label
    label = label.markup if isinstance(label, Text) else str(label)
    return DisplayTree(label=label, children=[tree_to_rpc(c) for c in tree.children])


def _split_path(path) -> tuple[str, str]:
    """[group_id, parent, label] -> ("group_id", "parent__label") as the backend expects."""
    if len(path) < 2:
        raise ValueError(f"Path must be [group, ..., node], got {list(path)}")
    return path[0], "__".join(path[1:])


# ---------------------------------------------------------------------------
# Preconditions
# ---------------------------------------------------------------------------


def requires_boot(method):
    @functools.wraps(method)
    def wrapper(self: RunconfService, request, context: grpc.ServicerContext):
        if self._backend is None:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION, "Not booted; call boot first"
            )
        return method(self, request, context)

    return wrapper


def requires_open(method):
    @requires_boot
    @functools.wraps(method)
    def wrapper(self: RunconfService, request, context: grpc.ServicerContext):
        if self._backend.configuration is None:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                "No configuration open; call open_configuration first",
            )
        return method(self, request, context)

    return wrapper


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RunconfService(runconf_services_pb2_grpc.RunconfServiceServicer):
    def __init__(self) -> None:
        self._backend: RunconfUIBackend | None = None
        self._frontend_endpoint: str | None = None
        # Dropdown values go over the wire as strings, but the backend may hand out
        # other types (e.g. Path for local sessions). Map the strings back.
        self._choices: dict[str, dict[str, Any]] = {}
        # Set by QUIT / CREATE_QUIT; run_until_quit() waits on it and stops the server.
        self.quit_requested = threading.Event()

    # ---- helpers ----

    def _snapshot(self) -> dict[PathKey, NodeStatusInfo]:
        """Flat view of every toggle/adjustable node, keyed by full path."""
        out: dict[PathKey, NodeStatusInfo] = {}
        groups = (
            (NodeGroup.TOGGLES, self._backend.get_excludable_values()),
            (NodeGroup.ADJUSTABLE, self._backend.get_adjustable_values()),
        )
        for node_group, by_group in groups:
            for group_id, nodes in by_group.items():
                for status in nodes.values():
                    info = node_to_rpc(group_id, status, node_group)
                    out[(str(node_group), *info.node_path)] = info
        return out

    def _trees(self) -> list[NodeStatusInfo]:
        """One root per (node group, config group) whose children are its nodes."""
        roots: dict[tuple[int, str], NodeStatusInfo] = {}
        for info in self._snapshot().values():
            key = (info.node_group, info.node_path[0])
            if key not in roots:
                roots[key] = NodeStatusInfo(
                    node_path=[info.node_path[0]], node_group=info.node_group
                )
            roots[key].children.append(info)
        return list(roots.values())

    @staticmethod
    def _diff(before, after) -> list[NodeStatusInfo]:
        return [n for k, n in after.items() if before.get(k) != n]

    def _dropdowns(self) -> dict[str, DropDownContent]:
        self._choices = {
            "version": {str(v): v for v in self._backend.get_daq_versions()},
            "session": {str(s): s for s in self._backend.get_sessions()},
        }
        return {k: DropDownContent(values=list(v)) for k, v in self._choices.items()}

    def _choice(self, key: str, value: str) -> Any:
        if not value:
            return None
        try:
            return self._choices[key][value]
        except KeyError:
            raise ValueError(f"{value!r} is not an available {key}") from None

    # ---- rpcs ----

    def boot(
        self, request: BootRequest, context: grpc.ServicerContext
    ) -> Initialisation:
        def opt(field: str) -> str | None:
            return getattr(request, field) if request.HasField(field) else None

        try:
            ctx = RunconfContext(
                apparatus=request.apparatus,
                conf_directory=Path(request.conf_directory),
                repo_type=RepoManagerType.from_string(request.manager_type),
                config_file_name=opt("config_file_name"),
                base_url=opt("base_url"),
                ops_url=opt("ops_url"),
                output_directory=Path(request.output_directory or "shifter-configs"),
            )
            self._backend = RunconfUIBackend(ctx)
            dropdowns = self._dropdowns()
            default_version = self._backend.get_default_version()
        except _EXPECTED_ERRORS as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Boot failed: {e}")

        self._frontend_endpoint = request.frontend_endpoint.url
        return Initialisation(
            daq_version=str(self._backend.get_current_version() or ""),
            apparatus=self._backend.apparatus,
            # structure holds the initial value for each dropdown
            structure={"version": str(default_version or "")},
            dropdowns=dropdowns,
        )

    @requires_boot
    def select_dropdown(
        self, request: DropDownSelection, context: grpc.ServicerContext
    ) -> DropDownUpdate:
        key = request.key.lower()
        resets: list[str] = []
        try:
            if key == "version":
                self._backend.set_daq_version(self._choice(key, request.value))
                resets = ["session"]
            elif key == "session":
                self._backend.set_daq_session(self._choice(key, request.value))
            else:
                raise KeyError(f"Unknown dropdown {request.key!r}")
            response = ok(f"Set {key} to {request.value}")
        except _EXPECTED_ERRORS as e:
            response = fail(f"Failed to set {key}", e)

        try:
            update = self._dropdowns()
        except _EXPECTED_ERRORS as e:
            return DropDownUpdate(response=fail("Failed to list dropdown values", e))
        return DropDownUpdate(response=response, update=update, resets=resets)

    @requires_boot
    def open_configuration(
        self, request: Open, context: grpc.ServicerContext
    ) -> ConfigurationOutcome:
        try:
            self._backend.open_selected_session()
        except _EXPECTED_ERRORS as e:
            return ConfigurationOutcome(
                response=fail("Failed to open configuration", e)
            )
        return ConfigurationOutcome(
            response=ok("Opened configuration"), config_trees=self._trees()
        )

    @requires_open
    def get_node_state(
        self, request: RequestNodeStatus, context: grpc.ServicerContext
    ) -> ResponseNodeStatus:
        lookup = (
            self._backend.get_adjustable_values
            if request.node_group == NodeGroup.ADJUSTABLE
            else self._backend.get_excludable_values
        )
        try:
            group_id, node_id = _split_path(request.path)
            status = lookup()[group_id][node_id]
        except _EXPECTED_ERRORS as e:
            return ResponseNodeStatus(
                response=fail(f"Node {list(request.path)} not found", e)
            )

        return ResponseNodeStatus(
            response=ok(f"Found {node_id}"),
            nodes=[node_to_rpc(group_id, status, request.node_group)],
        )

    @requires_open
    def set_node_state(
        self, request: RequestSetNodeValue, context: grpc.ServicerContext
    ) -> ResponseNodeStatus:
        kind = request.WhichOneof("node_value")
        try:
            group_id, node_id = _split_path(request.path)
            if kind is None:
                raise ValueError("node_value not set")
            if kind == "node_status_value":
                if request.node_status_value == NodeStatusRpc.PARENT_EXCLUDED:
                    raise ValueError("PARENT_EXCLUDED is derived and cannot be set")
                value = request.node_status_value == NodeStatusRpc.INCLUDED
            else:
                value = getattr(request, kind)

            before = self._snapshot()
            if request.node_group == NodeGroup.TOGGLES:
                # Same path the TUI takes: toggle within the excludable collection.
                current = self._backend.get_excludable_values()[group_id][node_id]
                if bool(value) != bool(current.node.get()):
                    self._backend.toggle(group_id, node_id)
            else:
                self._backend.set_value(group_id, node_id, value)
            changed = self._diff(before, self._snapshot())
        except _EXPECTED_ERRORS as e:
            return ResponseNodeStatus(
                response=fail(f"Failed to set {list(request.path)}", e)
            )

        return ResponseNodeStatus(
            response=ok(f"Set {node_id} to {value}"), nodes=changed
        )

    @requires_open
    def reset_node_state(
        self, request: RequestReset, context: grpc.ServicerContext
    ) -> ResponseNodeStatus:
        # Simplest correct reset: reopen the selected session from the repo.
        try:
            self._backend.open_selected_session()
        except _EXPECTED_ERRORS as e:
            return ResponseNodeStatus(response=fail("Reset failed", e))
        return ResponseNodeStatus(
            response=ok("Reset"), nodes=list(self._snapshot().values())
        )

    @requires_boot
    def get_views(
        self, request: RequestViews, context: grpc.ServicerContext
    ) -> DisplayViews:
        b = self._backend
        views = DisplayViews(
            response=ok("Views"),
            config_open=b.configuration is not None,
            info_text=b.info_text,
        )
        try:
            if b.configuration is not None:
                views.config_tree.CopyFrom(tree_to_rpc(b.get_config_tree()))
            for group_id, tree in b.get_tree_views().items():
                views.group_trees.append(
                    GroupTree(group_id=group_id, tree=tree_to_rpc(tree))
                )
            if b.config_session is not None:
                views.session_name = b.config_session.id
        except _EXPECTED_ERRORS as e:
            return DisplayViews(response=fail("Failed to render views", e))
        return views

    def runconf_command(
        self, request: RunconfCommandRequest, context: grpc.ServicerContext
    ) -> RunconfCommandResponse:
        cmd = request.command

        # Commands that do not need a backend
        if cmd == RunconfCommand.QUIT:
            self.quit_requested.set()
            return _command_response(cmd, ok("Shutting down without saving"))
        if cmd == RunconfCommand.HELP:
            return _command_response(cmd, ok("Help"), StringValue(value=HELP_TEXT))

        if cmd not in (RunconfCommand.CREATE_QUIT, RunconfCommand.RESET):
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Unknown command {cmd}")
        if self._backend is None:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION, "Not booted; call boot first"
            )

        try:
            if cmd == RunconfCommand.CREATE_QUIT:
                if self._backend.configuration is None:
                    raise ValueError("No configuration open; nothing to create")
                self._backend.save_config()
                self.quit_requested.set()
                return _command_response(
                    cmd,
                    ok("Configuration saved; shutting down"),
                    StringValue(value=str(self._backend.final_save_path)),
                )
            # RESET
            self._backend.open_selected_session()
            return _command_response(
                cmd, ok("Reset"), ConfigurationOutcome(config_trees=self._trees())
            )
        except _EXPECTED_ERRORS as e:
            return _command_response(cmd, fail(f"{RunconfCommand.Name(cmd)} failed", e))


HELP_TEXT = """runconf-ui gRPC service
  1. boot               - initialise the backend, returns dropdown contents
  2. select_dropdown    - pick 'version', then 'session'
  3. open_configuration - load the selected session, returns the node trees
  4. get/set_node_state - inspect or change toggles and adjustable values
  5. get_views          - pre-rendered trees and info text for display
  runconf_command: QUIT (no save), CREATE_QUIT (save then quit), RESET, HELP
"""


def _command_response(cmd, response: Response, details=None) -> RunconfCommandResponse:
    out = RunconfCommandResponse(command=cmd, response=response)
    if details is not None:
        out.details.Pack(details)
    return out


def serve(address: str = "[::]:50051") -> tuple[grpc.Server, RunconfService, int]:
    """Start the service. One worker because the backend is not thread-safe.

    :returns: (server, service, bound port). Pass port 0 in ``address`` to pick a free one.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    service = RunconfService()
    runconf_services_pb2_grpc.add_RunconfServiceServicer_to_server(service, server)
    port = server.add_insecure_port(address)
    server.start()
    return server, service, port


def run_until_quit(address: str = "[::]:50051", grace: float = 1.0) -> None:
    """Serve until a QUIT/CREATE_QUIT command arrives, then shut down."""
    server, service, _ = serve(address)
    service.quit_requested.wait()
    server.stop(grace).wait()
