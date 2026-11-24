"""
Client-side stand-in for RunconfUIBackend that talks to RunconfService over gRPC.

RpcBackend exposes the subset of the RunconfUIBackend interface used by the
Textual frontend, so RunconfUIApp can be pointed at either one unchanged. The
server's state is shared by all its frontends; RpcBackend follows it through a
``subscribe`` stream, so every frontend shows every user's changes.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import grpc
from google.protobuf.wrappers_pb2 import StringValue
from rich.tree import Tree
from runconfschema import runconf_services_pb2_grpc
from runconfschema.common_pb2 import OutcomeFlag
from runconfschema.configuration_access_pb2 import (
    ConfigurationInfo,
    DropDownSelection,
    Open,
    RequestConfigurationInfo,
)
from runconfschema.main_controls_pb2 import RunconfCommand, RunconfCommandRequest
from runconfschema.state_pb2 import (
    GroupNodes,
    NodeGroup,
    NodeStatusInfo,
    RequestNodeGroups,
    RequestSetNodeValue,
)
from runconfschema.state_pb2 import NodeStatus as NodeStatusRpc
from runconfschema.subscription_pb2 import RequestSubscribe, StateUpdate

from runconf_ui.api.grpc_service import REVISION_KEY
from runconf_ui.exceptions import LoggerNotFound, _RunconfUIException
from runconf_ui.state_tree import NodeStatus, State
from runconf_ui.utils import LogLevels, get_logger, init_logger
from runconf_ui.utils.rendering import (
    ConfigInfo,
    DrawItem,
    format_info_text,
    render_config_tree,
    render_panel_tree,
)

_STATE_FROM_RPC = {
    NodeStatusRpc.INCLUDED: State.INCLUDED,
    NodeStatusRpc.EXCLUDED: State.EXCLUDED,
    NodeStatusRpc.PARENT_EXCLUDED: State.PARENT_EXCLUDED,
}

NodeMap = dict[str, dict[str, NodeStatus]]


class RpcBackendError(_RunconfUIException):
    """The service answered with a FAIL response."""


# ---------------------------------------------------------------------------
# Lightweight node stand-ins. NodeStatus only needs .label/.tooltip/.get() on
# the node and .label on the parent, so these are enough for the widgets.
# ---------------------------------------------------------------------------


@dataclass
class RemoteNode:
    label: str
    tooltip: str
    value: Any

    def get(self) -> Any:
        return self.value


@dataclass
class RemoteParent:
    label: str


@dataclass
class RemoteSession:
    id: str


def rpc_value(info: NodeStatusInfo) -> Any:
    kind = info.WhichOneof("value")
    return getattr(info, kind) if kind else None


def node_from_rpc(info: NodeStatusInfo) -> tuple[str, str, NodeStatus]:
    """NodeStatusInfo -> (group_id, node_id, NodeStatus) matching the backend's keys."""
    group_id, *rest = info.node_path
    parent = RemoteParent(rest[0]) if len(rest) > 1 else None
    status = NodeStatus(
        node=RemoteNode(rest[-1], info.tooltip, rpc_value(info)),  # type: ignore[arg-type]
        state=_STATE_FROM_RPC[info.node_state],
        parent=parent,  # type: ignore[arg-type]
    )
    return group_id, "__".join(rest), status


def node_tree_from_rpc(info: NodeStatusInfo) -> DrawItem:
    """Nested NodeStatusInfo (a system hierarchy) -> DrawItem tree for rendering."""
    return DrawItem(
        label=info.label,
        state=_STATE_FROM_RPC[info.node_state],
        children=[node_tree_from_rpc(c) for c in info.children],
        source=info,
    )


def config_tree_from_rpc(nodes) -> list[DrawItem]:
    """ConfigTreeNodes -> DrawItems (relationship entries have no state)."""
    return [
        DrawItem(
            label=n.label,
            state=_STATE_FROM_RPC[n.state] if n.HasField("state") else None,
            children=config_tree_from_rpc(n.children),
            source=n,
        )
        for n in nodes
    ]


def _optional(msg, field: str) -> str | None:
    return getattr(msg, field) if msg.HasField(field) else None


def _ensure_logger(log_file: Path, log_level: LogLevels) -> None:
    """The TUI logs via the global runconf-ui logger, which RunconfUIBackend normally
    creates. When the server runs in another process nobody has, so make a
    frontend log. (In-process servers have already created one during boot.)"""
    try:
        get_logger()
    except LoggerNotFound:
        init_logger(log_file, log_level)


def _connect_error(address: str, error: grpc.RpcError) -> RpcBackendError:
    """Readable error for the common ways connecting to a server fails."""
    code = error.code()
    if code == grpc.StatusCode.UNAVAILABLE:
        return RpcBackendError(
            f"No runconf-ui server is reachable at {address}. "
            "Start one with: runconf-ui-server -g <address> -a <apparatus>"
        )
    if code == grpc.StatusCode.FAILED_PRECONDITION:
        return RpcBackendError(
            f"The runconf-ui server at {address} has not been booted yet "
            "(it is waiting for a boot request)."
        )
    if code == grpc.StatusCode.UNIMPLEMENTED:
        return RpcBackendError(
            f"The runconf-ui server at {address} does not support 'subscribe': "
            "it is running an older runconf-ui or runconfschema than this frontend."
        )
    return RpcBackendError(f"Could not connect to {address}: {error.details()}")


def _session_from_wire(s: str) -> str | Path:
    # Local sessions are config file paths; the TUI displays those by file name.
    return Path(s) if os.path.isabs(s) else s


@dataclass(frozen=True)
class StateChange:
    """What a listener hears after the shared state changed.

    kind is "snapshot" (dropdowns, open or reset: redraw everything), "nodes"
    (some node values changed), "shutdown" (the server is stopping) or
    "disconnected" (the stream broke). The cache already reflects the change.
    """

    kind: str
    revision: int
    message: str = ""


class RpcBackend:
    """Drop-in replacement for RunconfUIBackend backed by a RunconfService.

    The server's state is shared with every other frontend. A background thread
    keeps a ``subscribe`` stream open and applies each change to a local cache,
    which the getters read; register with ``add_listener`` to hear about them.
    """

    def __init__(
        self,
        address: str,
        timeout: float | None = None,
        log_dir: Path = Path("shifter-configs"),
        log_level: LogLevels = "INFO",
    ):
        """Connect to an already-booted service at ``address``.

        The server owns the context (apparatus, repositories, output directory);
        the frontend only needs to know where to find it.

        :param timeout: per-call deadline in seconds (None = wait forever, since
            opening a config or listing remote sessions can be slow)
        :param log_dir: where to write the frontend log if this process has none yet
        """
        self._channel = grpc.insecure_channel(address)
        self._stub = runconf_services_pb2_grpc.RunconfServiceStub(self._channel)
        self._timeout = timeout

        # The listener thread writes the cache, TUI threads read it. The condition
        # also tells callers when the stream has caught up with their own call.
        self._state = threading.Condition()
        self._revision = 0
        self._snapshot_revision = 0
        self._listeners: list[Callable[[StateChange], None]] = []
        self._dropdowns: dict[str, list[str]] = {}
        self._selection: dict[str, str] = {}
        self._toggles: NodeMap = {}
        self._adjustables: NodeMap = {}
        # Full node state and configuration summary, refetched lazily after changes
        self._groups: list[GroupNodes] | None = None
        self._info: ConfigurationInfo | None = None
        self._session_name: str | None = None
        self._open = False
        self._final_save_path: Path | None = None
        self._closed = False
        self._listening = True
        self._shutdown: str | None = None  # server's message once it shut down

        try:
            self._stream = self._stub.subscribe(RequestSubscribe())
            first = next(self._stream)
        except grpc.RpcError as e:
            self._channel.close()
            raise _connect_error(address, e) from e
        init = first.snapshot.initialisation
        self.apparatus = init.apparatus
        _ensure_logger(log_dir / f"{init.apparatus}_frontend.log", log_level)
        self._default_version = init.structure.get("version") or None
        self._apply(first)

        self._thread = threading.Thread(
            target=self._listen, name="runconf-subscribe", daemon=True
        )
        self._thread.start()

    # ------------------------------------------------------------------ #
    # Shared state stream                                                  #
    # ------------------------------------------------------------------ #

    def add_listener(self, listener: Callable[[StateChange], None]) -> None:
        """Call ``listener`` after each change to the shared state, from the
        stream's thread. It must not block (e.g. post a message to the UI)."""
        self._listeners.append(listener)

    @property
    def revision(self) -> int:
        """Revision of the shared state the cache reflects."""
        return self._revision

    @property
    def snapshot_revision(self) -> int:
        """Revision of the last full snapshot: changes when the node structure may have."""
        return self._snapshot_revision

    def _listen(self) -> None:
        change = None
        try:
            while True:
                for update in self._stream:
                    change = self._apply(update)
                    self._notify(change)
                    if change.kind == "shutdown":
                        return
                if self._closed:
                    return
                # The server dropped us for falling behind: start again from a snapshot
                get_logger().warning("Subscription ended; resubscribing")
                self._stream = self._stub.subscribe(RequestSubscribe())
        except grpc.RpcError as e:
            if not self._closed:
                get_logger().error(f"Lost the connection to the server: {e.details()}")
                self._notify(
                    StateChange("disconnected", self._revision, e.details() or "")
                )
        finally:
            with self._state:
                self._listening = False
                self._state.notify_all()

    def _notify(self, change: StateChange) -> None:
        for listener in list(self._listeners):
            try:
                listener(change)
            except Exception:
                get_logger().exception("State listener failed")

    def _apply(self, update: StateUpdate) -> StateChange:
        """Fold one update from the stream into the cache."""
        kind = update.WhichOneof("update")
        message = ""
        with self._state:
            if kind == "snapshot":
                state = update.snapshot
                self._update_dropdowns(state.initialisation.dropdowns)
                self._selection = dict(state.selection)
                self._open = state.config_open
                self._apply_groups(state.groups)
                self._info = None
                self._snapshot_revision = update.revision
            elif kind == "nodes":
                self._merge_nodes(update.nodes.nodes)
            elif kind == "shutdown":
                message = update.shutdown.response.message
                path = StringValue()
                if update.shutdown.details.Unpack(path):
                    self._final_save_path = Path(path.value)
                self._shutdown = message
            self._revision = max(self._revision, update.revision)
            self._state.notify_all()
        return StateChange(kind or "", update.revision, message)

    def _wait_for(self, revision: int) -> None:
        """Block until the stream has delivered ``revision`` (or has stopped)."""
        with self._state:
            if not self._state.wait_for(
                lambda: self._revision >= revision or not self._listening,
                timeout=self._timeout or 30,
            ):
                get_logger().warning(f"Stream has not caught up with revision {revision}")

    # ------------------------------------------------------------------ #
    # Plumbing                                                             #
    # ------------------------------------------------------------------ #

    def _call(self, rpc, request):
        """Unary call; once it returns, the cache includes its effect."""
        reply, _ = self._call_at(rpc, request)
        return reply

    def _call_at(self, rpc, request):
        """Like _call, also returning the revision the server answered at."""
        if self._shutdown is not None:
            raise RpcBackendError(f"The server has shut down: {self._shutdown}")
        reply, call = rpc.with_call(request, timeout=self._timeout)
        revision = int(dict(call.trailing_metadata() or ()).get(REVISION_KEY, 0))
        self._wait_for(revision)
        response = getattr(reply, "response", None)
        if response is not None and response.outcome == OutcomeFlag.FAIL:
            detail = response.error.message if response.HasField("error") else ""
            raise RpcBackendError(f"{response.message}: {detail}".rstrip(": "))
        return reply, revision

    def _update_dropdowns(self, update) -> None:
        for key, content in update.items():
            self._dropdowns[key] = list(content.values)

    def _apply_groups(self, groups) -> None:
        """Replace the cached node state with a full set of groups from the server."""
        self._groups = list(groups)
        self._toggles, self._adjustables = {}, {}
        for group in self._groups:
            target = (
                self._adjustables
                if group.node_group == NodeGroup.ADJUSTABLE
                else self._toggles
            )
            nodes = target.setdefault(group.group_id, {})
            for info in group.nodes:
                _, node_id, status = node_from_rpc(info)
                nodes[node_id] = status

    def _merge_nodes(self, infos) -> None:
        """Apply changed nodes to the flat cache; hierarchies are refetched lazily."""
        for info in infos:
            target = (
                self._adjustables
                if info.node_group == NodeGroup.ADJUSTABLE
                else self._toggles
            )
            group_id, node_id, status = node_from_rpc(info)
            target.setdefault(group_id, {})[node_id] = status
        self._groups = None
        self._info = None

    def _get_groups(self) -> list[GroupNodes]:
        with self._state:
            if self._groups is not None or not self._open:
                return self._groups or []
        reply, revision = self._call_at(self._stub.get_node_groups, RequestNodeGroups())
        with self._state:
            # Only cache it if nobody changed anything since the server built it
            if self._revision == revision:
                self._apply_groups(reply.groups)
        return list(reply.groups)

    def _get_info(self) -> ConfigurationInfo:
        with self._state:
            if self._info is not None:
                return self._info
        info, revision = self._call_at(
            self._stub.get_configuration_info, RequestConfigurationInfo()
        )
        with self._state:
            if self._revision == revision:
                self._info = info
            self._session_name = _optional(info, "session_name")
        return info

    def _set(self, group: NodeGroup, group_id: str, node_id: str, **value) -> None:
        request = RequestSetNodeValue(
            node_group=group, path=[group_id, *node_id.split("__")], **value
        )
        self._call(self._stub.set_node_state, request)

    def _command(self, command: RunconfCommand):
        return self._call(
            self._stub.runconf_command, RunconfCommandRequest(command=command)
        )

    # ------------------------------------------------------------------ #
    # Session / version                                                    #
    # ------------------------------------------------------------------ #

    def get_daq_versions(self) -> list[str]:
        return self._dropdowns.get("version", [])

    def get_default_version(self) -> str | None:
        return self._default_version

    def get_current_version(self) -> str | None:
        return self._selection.get("version")

    def get_sessions(self) -> list[str | Path]:
        return [_session_from_wire(s) for s in self._dropdowns.get("session", [])]

    def get_current_session(self) -> str | Path | None:
        session = self._selection.get("session")
        return None if session is None else _session_from_wire(session)

    def set_daq_version(self, version) -> None:
        self._select("version", version)

    def set_daq_session(self, session: str | Path | None) -> None:
        self._select("session", session)

    def _select(self, key: str, value) -> None:
        self._call(
            self._stub.select_dropdown,
            DropDownSelection(key=key, value="" if value is None else str(value)),
        )

    # ------------------------------------------------------------------ #
    # Config lifecycle                                                     #
    # ------------------------------------------------------------------ #

    def open_selected_session(self) -> None:
        self._call(self._stub.open_configuration, Open())
        self._get_info()  # caches session_name for after the server has gone

    def save_config(self) -> None:
        """Save on the server. The service then shuts down for every frontend
        (CREATE_QUIT)."""
        reply = self._command(RunconfCommand.CREATE_QUIT)
        path = StringValue()
        if reply.details.Unpack(path):
            self._final_save_path = Path(path.value)
        self._closed = True

    def shutdown_server(self) -> None:
        """Stop the server without saving (QUIT), for every frontend."""
        self._command(RunconfCommand.QUIT)
        self._closed = True

    def close(self) -> None:
        """Disconnect. The server keeps running for the other frontends; stop it
        with ``shutdown_server`` (or ``save_config``)."""
        self._closed = True
        self._stream.cancel()
        self._channel.close()
        if self._thread is not threading.current_thread():
            self._thread.join(timeout=5)

    @property
    def shutdown_message(self) -> str | None:
        """The server's message if it has shut down (someone quit or saved)."""
        return self._shutdown

    @property
    def configuration(self):
        """Truthy when a configuration is open (the TUI only checks ``is not None``)."""
        return True if self._open else None

    @property
    def config_session(self) -> RemoteSession | None:
        if not self._open or self._session_name is None:
            return None
        return RemoteSession(self._session_name)

    @property
    def final_save_path(self) -> Path:
        # Only known once CREATE_QUIT succeeds. Before that, return a path that is
        # never a regular file so callers (get_exit_msg) report "not created".
        return self._final_save_path or Path(os.devnull)

    # ------------------------------------------------------------------ #
    # State                                                              #
    # ------------------------------------------------------------------ #

    def get_excludable_values(self) -> NodeMap:
        with self._state:
            return {g: dict(n) for g, n in self._toggles.items()}

    def get_adjustable_values(self) -> NodeMap:
        with self._state:
            return {g: dict(n) for g, n in self._adjustables.items()}

    def toggle(self, group: str, node_id: str) -> None:
        current = self._toggles[group][node_id]
        self._set(NodeGroup.TOGGLES, group, node_id, bool_value=not current.node.get())

    def set_value(self, group: str, node_id: str, value) -> None:
        if isinstance(value, bool):
            kw = {"bool_value": value}
        elif isinstance(value, int):
            kw = {"int_value": value}
        elif isinstance(value, float):
            kw = {"double_value": value}
        else:  # raw text from the TUI input box: let the backend interpret it
            kw = {"string_value": str(value)}
        self._set(NodeGroup.ADJUSTABLE, group, node_id, **kw)

    # ------------------------------------------------------------------ #
    # Display: rendered locally from structured data                       #
    # ------------------------------------------------------------------ #

    def get_tree_views(self) -> dict[str, Tree]:
        return {
            g.group_id: render_panel_tree(
                g.view_panel, [node_tree_from_rpc(s) for s in g.systems]
            )
            for g in self._get_groups()
            if g.HasField("view_panel")
        }

    def get_config_tree(self) -> Tree:
        if not self._open:
            return render_config_tree(None, [])
        info = self._get_info()
        return render_config_tree(
            _optional(info, "session_name"), config_tree_from_rpc(info.config_tree)
        )

    @property
    def config_info(self) -> ConfigInfo | None:
        if not self._open:
            return None
        info = self._get_info()
        return ConfigInfo(
            daq_version=_optional(info, "daq_version"),
            apparatus=info.apparatus,
            config_file=_optional(info, "config_file"),
            current_file=_optional(info, "current_file"),
            session_name=_optional(info, "session_name"),
        )

    @property
    def info_text(self) -> str:
        return format_info_text(self.config_info)
