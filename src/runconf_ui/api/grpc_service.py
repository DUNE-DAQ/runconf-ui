"""
gRPC service exposing RunconfUIBackend via the runconfschema protobufs.

The server runs on an asyncio event loop (grpc.aio). Every frontend connected to
it shares one backend, and each keeps a ``subscribe`` stream open: whenever any
frontend changes the shared state, the server pushes the change to all of them.
"""

from __future__ import annotations

import asyncio
import dataclasses
import functools
import threading
from collections.abc import AsyncIterator, Callable
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
from runconfschema.subscription_pb2 import RequestSubscribe, ServerState, StateUpdate

from runconf_ui.backend import RunconfContext, RunconfUIBackend
from runconf_ui.exceptions import _RunconfUIException
from runconf_ui.repo_manager import RepoManagerType
from runconf_ui.state_tree import NodeStatus, State
from runconf_ui.utils.rendering import DrawItem

# Exceptions we turn into a FAIL Response rather than a gRPC error.
_EXPECTED_ERRORS = (_RunconfUIException, KeyError, ValueError, OSError)

PathKey = tuple[str, ...]

# Trailing metadata on every unary reply: the revision of the shared state once
# the call has been handled. Clients wait for their stream to reach it, so what
# they show includes their own change.
REVISION_KEY = "runconf-revision"

# Updates a subscriber may fall behind by before we drop it. Its stream then
# ends, and a client that resubscribes starts again from a fresh snapshot.
SUBSCRIBER_BUFFER = 256
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


class _Abort(Exception):
    """Raised from backend code to end the call with a gRPC error status."""

    def __init__(self, code: grpc.StatusCode, details: str):
        super().__init__(details)
        self.code = code
        self.details = details


_NOT_BOOTED = "Not booted; call boot first"
_NOT_OPEN = "No configuration open; call open_configuration first"


def _rpc(needs: str | None = None):
    """Turn a synchronous ``method(self, request)`` into an async gRPC handler.

    The backend is blocking and not thread-safe, so every call holds the service
    lock and runs on the single backend thread, keeping the event loop free to
    serve the subscription streams meanwhile. Updates the method publishes are
    sent to subscribers before the reply goes out.

    :param needs: None, "boot" (backend must exist) or "open" (config must be open)
    """

    def decorate(method):
        @functools.wraps(method)
        async def handler(self: RunconfService, request, context: grpc.aio.ServicerContext):
            def checked():
                if needs is not None and self._backend is None:
                    raise _Abort(grpc.StatusCode.FAILED_PRECONDITION, _NOT_BOOTED)
                if needs == "open" and self._backend.configuration is None:
                    raise _Abort(grpc.StatusCode.FAILED_PRECONDITION, _NOT_OPEN)
                return method(self, request)

            async with self._lock:
                try:
                    reply = await self._in_backend_thread(checked)
                except _Abort as e:
                    await context.abort(e.code, e.details)
                finally:
                    self._flush()
                context.set_trailing_metadata(((REVISION_KEY, str(self._revision)),))
            return reply

        return handler

    return decorate


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RunconfService(runconf_services_pb2_grpc.RunconfServiceServicer):
    """One backend, booted once with a context shared by every frontend.

    Boot either with ``start`` (the server's own CLI does this, through ``serve``)
    or with a single ``boot`` RPC from whoever launches the server. Frontends
    then ``subscribe``: they get a snapshot of the shared state, and from then on
    every change any frontend makes, so they all show the same thing.
    """

    def __init__(self, log_to_terminal: bool = True) -> None:
        """
        :param log_to_terminal: also log to the terminal. Turn off when the server
            shares a process with the TUI, or the logs draw over it.
        """
        self._log_to_terminal = log_to_terminal
        self._backend: RunconfUIBackend | None = None
        self._frontend_endpoint: str | None = None
        # Dropdown values go over the wire as strings, but the backend may hand out
        # other types (e.g. Path for local sessions). Map the strings back.
        self._choices: dict[str, dict[str, Any]] = {}

        # All backend calls run on this one thread, one at a time (see _rpc)
        self._executor = futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="runconf-backend"
        )
        self._lock = asyncio.Lock()
        self._subscribers: set[asyncio.Queue[StateUpdate | None]] = set()
        self._revision = 0
        self._pending: list[StateUpdate] = []  # published by the current call
        # Set by QUIT / CREATE_QUIT; run_until_quit() waits on it and stops the server.
        self.quit_requested = asyncio.Event()

    async def start(self, ctx: RunconfContext) -> None:
        """Boot the backend with ``ctx`` (instead of waiting for a boot RPC)."""
        async with self._lock:
            await self._in_backend_thread(self._boot_backend, ctx)

    def close(self) -> None:
        """Release the backend thread. Call once the server has stopped."""
        self._executor.shutdown(wait=False, cancel_futures=True)

    # ---- event loop plumbing ----

    async def _in_backend_thread(self, fn: Callable, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, functools.partial(fn, *args))

    def _publish(self, **update) -> None:
        """Queue an update for every subscriber (sent once the current call is done).
        Safe from the backend thread: the caller holds the service lock."""
        self._revision += 1
        self._pending.append(StateUpdate(revision=self._revision, **update))

    def _flush(self) -> None:
        """Hand the current call's updates to the subscribers (on the event loop)."""
        pending, self._pending = self._pending, []
        for update in pending:
            for queue in list(self._subscribers):
                try:
                    queue.put_nowait(update)
                except asyncio.QueueFull:
                    # Too far behind: end its stream rather than let it miss updates
                    self._subscribers.discard(queue)
                    while not queue.empty():
                        queue.get_nowait()
                    queue.put_nowait(None)
            if update.HasField("shutdown"):
                self.quit_requested.set()

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

    def _server_state(self) -> ServerState:
        """Everything a frontend needs to draw the shared state from scratch."""
        selection = {}
        for key, value in (
            ("version", self._backend.get_current_version()),
            ("session", self._backend.get_current_session()),
        ):
            if value is not None:
                selection[key] = str(value)
        state = ServerState(
            initialisation=self._initialisation(),
            selection=selection,
            config_open=self._backend.configuration is not None,
        )
        if state.config_open:
            state.groups.extend(self._groups())
        return state

    def _publish_snapshot(self) -> None:
        self._publish(snapshot=self._server_state())

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

    # ---- streaming ----

    async def subscribe(
        self, request: RequestSubscribe, context: grpc.aio.ServicerContext
    ) -> AsyncIterator[StateUpdate]:
        """A snapshot of the shared state, then every change until the server stops."""
        queue: asyncio.Queue[StateUpdate | None] = asyncio.Queue(SUBSCRIBER_BUFFER)
        async with self._lock:
            if self._backend is None:
                await context.abort(grpc.StatusCode.FAILED_PRECONDITION, _NOT_BOOTED)
            try:
                state = await self._in_backend_thread(self._server_state)
            except _EXPECTED_ERRORS as e:
                await context.abort(
                    grpc.StatusCode.INTERNAL, f"Cannot read server state: {e}"
                )
            # Registered under the lock, so no change slips between snapshot and queue
            first = StateUpdate(revision=self._revision, snapshot=state)
            self._subscribers.add(queue)
        try:
            yield first
            while (update := await queue.get()) is not None:
                yield update
                if update.HasField("shutdown"):
                    return
        finally:
            self._subscribers.discard(queue)

    # ---- rpcs ----

    @_rpc()
    def boot(self, request: BootRequest) -> Initialisation:
        if self._backend is not None:
            raise _Abort(
                grpc.StatusCode.ALREADY_EXISTS,
                f"Server already booted for {self._backend.apparatus}; "
                "frontends should call initialise",
            )
        try:
            self._boot_backend(context_from_boot_request(request))
            init = self._initialisation()
        except _EXPECTED_ERRORS as e:
            self._backend = None
            raise _Abort(grpc.StatusCode.INVALID_ARGUMENT, f"Boot failed: {e}") from e
        self._frontend_endpoint = request.frontend_endpoint.url
        return init

    @_rpc(needs="boot")
    def initialise(self, request: RequestInitialisation) -> Initialisation:
        try:
            return self._initialisation()
        except _EXPECTED_ERRORS as e:
            raise _Abort(
                grpc.StatusCode.INTERNAL, f"Cannot read server state: {e}"
            ) from e

    @_rpc(needs="boot")
    def select_dropdown(self, request: DropDownSelection) -> DropDownUpdate:
        key = request.key.lower()
        resets: list[str] = []
        try:
            if key == "version":
                self._backend.set_daq_version(self._choice(key, request.value))
                # The old session belongs to the old version; every frontend resets it
                self._backend.set_daq_session(None)
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
            if response.outcome == OutcomeFlag.SUCCESS:
                self._publish_snapshot()
        except _EXPECTED_ERRORS as e:
            return DropDownUpdate(response=fail("Failed to list dropdown values", e))
        return DropDownUpdate(response=response, update=update, resets=resets)

    @_rpc(needs="boot")
    def open_configuration(self, request: Open) -> ConfigurationOutcome:
        try:
            self._backend.open_selected_session()
            state = self._server_state()
        except _EXPECTED_ERRORS as e:
            return ConfigurationOutcome(
                response=fail("Failed to open configuration", e)
            )
        self._publish(snapshot=state)
        return ConfigurationOutcome(response=ok("Opened configuration"), groups=state.groups)

    @_rpc(needs="open")
    def get_node_state(self, request: RequestNodeStatus) -> ResponseNodeStatus:
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

    @_rpc(needs="open")
    def set_node_state(self, request: RequestSetNodeValue) -> ResponseNodeStatus:
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

        reply = ResponseNodeStatus(
            response=ok(f"Set {node_id} to {value}"), nodes=changed
        )
        if changed:
            self._publish(nodes=reply)
        return reply

    @_rpc(needs="open")
    def reset_node_state(self, request: RequestReset) -> ResponseNodeStatus:
        # Simplest correct reset: reopen the selected session from the repo.
        try:
            self._backend.open_selected_session()
            self._publish_snapshot()
        except _EXPECTED_ERRORS as e:
            return ResponseNodeStatus(response=fail("Reset failed", e))
        return ResponseNodeStatus(
            response=ok("Reset"), nodes=list(self._snapshot().values())
        )

    @_rpc(needs="open")
    def get_node_groups(self, request: RequestNodeGroups) -> ResponseNodeGroups:
        try:
            return ResponseNodeGroups(response=ok("Node groups"), groups=self._groups())
        except _EXPECTED_ERRORS as e:
            return ResponseNodeGroups(response=fail("Failed to read node groups", e))

    @_rpc(needs="boot")
    def get_configuration_info(
        self, request: RequestConfigurationInfo
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

    @_rpc()
    def runconf_command(self, request: RunconfCommandRequest) -> RunconfCommandResponse:
        cmd = request.command

        # Commands that do not need a backend
        if cmd == RunconfCommand.QUIT:
            reply = _command_response(cmd, ok("Shutting down without saving"))
            self._publish(shutdown=reply)
            return reply
        if cmd == RunconfCommand.HELP:
            return _command_response(cmd, ok("Help"), StringValue(value=HELP_TEXT))

        if cmd not in (RunconfCommand.CREATE_QUIT, RunconfCommand.RESET):
            raise _Abort(grpc.StatusCode.INVALID_ARGUMENT, f"Unknown command {cmd}")
        if self._backend is None:
            raise _Abort(grpc.StatusCode.FAILED_PRECONDITION, _NOT_BOOTED)

        try:
            if cmd == RunconfCommand.CREATE_QUIT:
                if self._backend.configuration is None:
                    raise ValueError("No configuration open; nothing to create")
                self._backend.save_config()
                reply = _command_response(
                    cmd,
                    ok("Configuration saved; shutting down"),
                    StringValue(value=str(self._backend.final_save_path)),
                )
                self._publish(shutdown=reply)
                return reply
            # RESET
            self._backend.open_selected_session()
            state = self._server_state()
            self._publish(snapshot=state)
            return _command_response(
                cmd, ok("Reset"), ConfigurationOutcome(groups=state.groups)
            )
        except _EXPECTED_ERRORS as e:
            return _command_response(cmd, fail(f"{RunconfCommand.Name(cmd)} failed", e))


HELP_TEXT = """runconf-ui gRPC service
  0. boot               - (once, by the launcher) boot the backend with the shared context
  1. subscribe          - (each frontend) snapshot of the shared state, then every
                           change any frontend makes (initialise: just the dropdowns)
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


async def serve_async(
    address: str = "[::]:50051",
    context: RunconfContext | None = None,
    log_to_terminal: bool = True,
) -> tuple[grpc.aio.Server, RunconfService, int]:
    """Start the service on the running event loop.

    :param context: boot with this context straight away (None = wait for a boot RPC)
    :returns: (server, service, bound port). Pass port 0 in ``address`` to pick a free one.
    """
    service = RunconfService(log_to_terminal=log_to_terminal)
    if context is not None:
        await service.start(context)
    server = grpc.aio.server()
    runconf_services_pb2_grpc.add_RunconfServiceServicer_to_server(service, server)
    port = server.add_insecure_port(address)
    await server.start()
    return server, service, port


async def run_until_quit_async(
    address: str = "[::]:50051",
    context: RunconfContext | None = None,
    grace: float = 1.0,
    on_started: Callable[[int], None] | None = None,
) -> None:
    """Serve on the running event loop until a QUIT/CREATE_QUIT command arrives.

    :param on_started: called with the bound port once the server is listening
    """
    server, service, port = await serve_async(address, context)
    try:
        if on_started is not None:
            on_started(port)
        await service.quit_requested.wait()
    finally:
        await server.stop(grace)
        service.close()


def run_until_quit(
    address: str = "[::]:50051",
    context: RunconfContext | None = None,
    grace: float = 1.0,
    on_started: Callable[[int], None] | None = None,
) -> None:
    """Run the server in its own event loop until a QUIT/CREATE_QUIT command arrives."""
    asyncio.run(run_until_quit_async(address, context, grace, on_started))


class BackgroundServer:
    """The asyncio server on an event loop of its own in a daemon thread, for
    callers that are not async themselves: tests, and the TUI's in-process
    server (Textual runs its own loop on the main thread).

    ``stop`` mirrors ``grpc.Server.stop``: it returns an event to ``wait()`` on.
    """

    def __init__(
        self, address: str, context: RunconfContext | None, log_to_terminal: bool
    ) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop, name="runconf-grpc-loop", daemon=True
        )
        self._thread.start()
        self._stopped: threading.Event | None = None
        try:
            self.server, self.service, self.port = asyncio.run_coroutine_threadsafe(
                serve_async(address, context, log_to_terminal), self._loop
            ).result()
        except BaseException:
            self._loop.call_soon_threadsafe(self._loop.stop)
            raise

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()

    def stop(self, grace: float | None) -> threading.Event:
        """Stop the server (and its loop); returns an event set once it has."""
        if self._stopped is not None:
            return self._stopped
        stopped = self._stopped = threading.Event()

        async def shutdown():
            await self.server.stop(grace)
            self.service.close()

        def done(_):
            self._loop.call_soon_threadsafe(self._loop.stop)
            stopped.set()

        asyncio.run_coroutine_threadsafe(shutdown(), self._loop).add_done_callback(done)
        return stopped


def serve(
    address: str = "[::]:50051",
    context: RunconfContext | None = None,
    log_to_terminal: bool = True,
) -> tuple[BackgroundServer, RunconfService, int]:
    """Start the service on a background event loop (see BackgroundServer).

    :param context: boot with this context straight away (None = wait for a boot RPC)
    :returns: (server, service, bound port). Pass port 0 in ``address`` to pick a free one.
    """
    server = BackgroundServer(address, context, log_to_terminal)
    return server, server.service, server.port
