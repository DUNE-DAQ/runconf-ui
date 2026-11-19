"""
gRPC service exposing RunconfUIBackend via the runconfschema protobufs.
"""

from __future__ import annotations

import dataclasses
import functools
import threading
from concurrent import futures
from pathlib import Path
from typing import Any

import grpc
from google.protobuf.wrappers_pb2 import StringValue
from runconfschema import runconf_services_pb2_grpc
from runconfschema.bootstrap_pb2 import BootRequest
from runconfschema.common_pb2 import Error, OutcomeFlag, Response
from runconfschema.configuration_access_pb2 import (
    ConfigTreeNode,
    ConfigurationInfo,
    ConfigurationOutcome,
    DropDownContent,
    DropDownSelection,
    DropDownUpdate,
    Initialisation,
    Open,
    RequestConfigurationInfo,
    RequestInitialisation,
)
from runconfschema.main_controls_pb2 import (
    RunconfCommand,
    RunconfCommandRequest,
    RunconfCommandResponse,
)
from runconfschema.state_pb2 import (
    GroupNodes,
    NodeGroup,
    NodeStatusInfo,
    RequestNodeGroups,
    RequestNodeStatus,
    RequestReset,
    RequestSetNodeValue,
    ResponseNodeGroups,
    ResponseNodeStatus,
)
from runconfschema.state_pb2 import NodeStatus as NodeStatusRpc

from runconf_ui.backend import RunconfContext, RunconfUIBackend
from runconf_ui.exceptions import _RunconfUIException
from runconf_ui.repo_manager import RepoManagerType
from runconf_ui.state_tree import NodeStatus, State
from runconf_ui.utils.rendering import DrawItem

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
        label=status.node.label,
    )
    set_typed_value(info, status.node.get())
    return info


def system_tree_to_rpc(
    item: DrawItem, group_id: str, node_group: int, index: dict
) -> NodeStatusInfo:
    """System hierarchy (DrawItems built from NodeStatus) -> nested NodeStatusInfo.
    Only nodes present in the group's index get a node_path."""
    status: NodeStatus = item.source
    info = NodeStatusInfo(
        node_state=_STATE_TO_RPC[item.state],
        label=item.label,
        tooltip=status.node.tooltip,
        node_group=node_group,
        children=[
            system_tree_to_rpc(c, group_id, node_group, index) for c in item.children
        ],
    )
    if status.path in index:
        info.node_path.extend([group_id, *status.path.split("__")])
    set_typed_value(info, status.node.get())
    return info


def config_items_to_rpc(items: list[DrawItem]) -> list[ConfigTreeNode]:
    out = []
    for item in items:
        node = ConfigTreeNode(
            label=item.label, children=config_items_to_rpc(item.children)
        )
        if item.state is not None:
            node.state = _STATE_TO_RPC[item.state]
        out.append(node)
    return out


def context_from_boot_request(request: BootRequest) -> RunconfContext:
    """BootRequest -> RunconfContext (unset optional fields become None)."""

    def opt(field: str) -> str | None:
        return getattr(request, field) if request.HasField(field) else None

    return RunconfContext(
        apparatus=request.apparatus,
        conf_directory=Path(request.conf_directory),
        repo_type=RepoManagerType.from_string(request.manager_type),
        config_file_name=opt("config_file_name"),
        base_url=opt("base_url"),
        ops_url=opt("ops_url"),
        output_directory=Path(request.output_directory or "shifter-configs"),
    )


def boot_request_from_context(ctx: RunconfContext) -> BootRequest:
    """RunconfContext -> BootRequest, for launchers that boot a server remotely."""
    request = BootRequest(
        apparatus=ctx.apparatus,
        manager_type=ctx.repo_type.value,
        conf_directory=str(ctx.conf_directory),
        output_directory=str(ctx.output_directory),
    )
    for field in ("config_file_name", "base_url", "ops_url"):
        value = getattr(ctx, field)
        if value:
            setattr(request, field, value)
    return request


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
    """One backend, booted once with a context shared by every frontend.

    Boot either by passing ``context`` here (the server's own CLI does this) or
    with a single ``boot`` RPC from whoever launches the server. Frontends then
    connect with ``initialise``.

    For now we run one server per user. Nothing below is per-frontend state, so
    several frontends could already share a server; they would see (and change)
    the same selections and configuration.
    """

    def __init__(
        self, context: RunconfContext | None = None, log_to_terminal: bool = True
    ) -> None:
        """
        :param context: boot straight away with this context (None = wait for boot RPC)
        :param log_to_terminal: also log to the terminal. Turn off when the server
            shares a process with the TUI, or the logs draw over it.
        """
        self._log_to_terminal = log_to_terminal
        self._backend: RunconfUIBackend | None = None
        self._frontend_endpoint: str | None = None
        # Dropdown values go over the wire as strings, but the backend may hand out
        # other types (e.g. Path for local sessions). Map the strings back.
        self._choices: dict[str, dict[str, Any]] = {}
        # Set by QUIT / CREATE_QUIT; run_until_quit() waits on it and stops the server.
        self.quit_requested = threading.Event()
        if context is not None:
            self._boot_backend(context)

    # ---- helpers ----

    def _boot_backend(self, ctx: RunconfContext) -> None:
        ctx = dataclasses.replace(ctx, log_to_terminal=self._log_to_terminal)
        self._backend = RunconfUIBackend(ctx)
        self._dropdowns()

    def _initialisation(self) -> Initialisation:
        return Initialisation(
            daq_version=str(self._backend.get_current_version() or ""),
            apparatus=self._backend.apparatus,
            # structure holds the initial value for each dropdown
            structure={"version": str(self._backend.get_default_version() or "")},
            dropdowns=self._dropdowns(),
        )

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

    def _groups(self) -> list[GroupNodes]:
        """Full node state: toggle groups, then adjustable groups."""
        excludable, adjustable = self._backend.get_groups()
        kinds = (
            (NodeGroup.TOGGLES, excludable, self._backend.get_excludable_values()),
            (NodeGroup.ADJUSTABLE, adjustable, self._backend.get_adjustable_values()),
        )
        out = []
        for node_group, groups, flat in kinds:
            for group in groups:
                index = flat.get(group.id, {})
                msg = GroupNodes(
                    group_id=group.id,
                    node_group=node_group,
                    nodes=[
                        node_to_rpc(group.id, s, node_group) for s in index.values()
                    ],
                    systems=[
                        system_tree_to_rpc(
                            self._backend.get_system_tree(system),
                            group.id,
                            node_group,
                            index,
                        )
                        for system in group.systems
                    ],
                )
                if group.view_panel:
                    msg.view_panel = group.view_panel
                out.append(msg)
        return out

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
        if self._backend is not None:
            context.abort(
                grpc.StatusCode.ALREADY_EXISTS,
                f"Server already booted for {self._backend.apparatus}; "
                "frontends should call initialise",
            )
        try:
            self._boot_backend(context_from_boot_request(request))
            init = self._initialisation()
        except _EXPECTED_ERRORS as e:
            self._backend = None
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Boot failed: {e}")
        self._frontend_endpoint = request.frontend_endpoint.url
        return init

    @requires_boot
    def initialise(
        self, request: RequestInitialisation, context: grpc.ServicerContext
    ) -> Initialisation:
        try:
            return self._initialisation()
        except _EXPECTED_ERRORS as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Cannot read server state: {e}")

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
            response=ok("Opened configuration"), groups=self._groups()
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

    @requires_open
    def get_node_groups(
        self, request: RequestNodeGroups, context: grpc.ServicerContext
    ) -> ResponseNodeGroups:
        try:
            return ResponseNodeGroups(response=ok("Node groups"), groups=self._groups())
        except _EXPECTED_ERRORS as e:
            return ResponseNodeGroups(response=fail("Failed to read node groups", e))

    @requires_boot
    def get_configuration_info(
        self, request: RequestConfigurationInfo, context: grpc.ServicerContext
    ) -> ConfigurationInfo:
        b = self._backend
        out = ConfigurationInfo(
            response=ok("Configuration info"),
            config_open=b.configuration is not None,
            apparatus=b.apparatus,
        )
        info = b.config_info
        if info is not None:
            for name in ("daq_version", "config_file", "current_file", "session_name"):
                value = getattr(info, name)
                if value is not None:
                    setattr(out, name, str(value))
        try:
            out.config_tree.extend(config_items_to_rpc(b.get_config_tree_items()))
        except _EXPECTED_ERRORS as e:
            return ConfigurationInfo(response=fail("Failed to read configuration", e))
        return out

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
                cmd, ok("Reset"), ConfigurationOutcome(groups=self._groups())
            )
        except _EXPECTED_ERRORS as e:
            return _command_response(cmd, fail(f"{RunconfCommand.Name(cmd)} failed", e))


HELP_TEXT = """runconf-ui gRPC service
  0. boot               - (once, by the launcher) boot the backend with the shared context
  1. initialise         - (each frontend) current dropdown contents and versions
  2. select_dropdown    - pick 'version', then 'session'
  3. open_configuration - load the selected session, returns the node trees
  4. get/set_node_state - inspect or change toggles and adjustable values
  5. get_node_groups / get_configuration_info - full state for drawing
  runconf_command: QUIT (no save), CREATE_QUIT (save then quit), RESET, HELP
"""


def _command_response(cmd, response: Response, details=None) -> RunconfCommandResponse:
    out = RunconfCommandResponse(command=cmd, response=response)
    if details is not None:
        out.details.Pack(details)
    return out


def serve(
    address: str = "[::]:50051",
    context: RunconfContext | None = None,
    log_to_terminal: bool = True,
) -> tuple[grpc.Server, RunconfService, int]:
    """Start the service. One worker because the backend is not thread-safe.

    :param context: boot with this context straight away (None = wait for a boot RPC)
    :returns: (server, service, bound port). Pass port 0 in ``address`` to pick a free one.
    """
    service = RunconfService(context, log_to_terminal=log_to_terminal)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    runconf_services_pb2_grpc.add_RunconfServiceServicer_to_server(service, server)
    port = server.add_insecure_port(address)
    server.start()
    return server, service, port


def run_until_quit(
    address: str = "[::]:50051",
    context: RunconfContext | None = None,
    grace: float = 1.0,
) -> None:
    """Serve until a QUIT/CREATE_QUIT command arrives, then shut down."""
    server, service, _ = serve(address, context)
    service.quit_requested.wait()
    server.stop(grace).wait()
