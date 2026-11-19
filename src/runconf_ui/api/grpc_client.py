"""
Client-side stand-in for RunconfUIBackend that talks to RunconfService over gRPC.

RpcBackend exposes the subset of the RunconfUIBackend interface used by the
Textual frontend, so RunconfUIApp can be pointed at either one unchanged.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import grpc
from google.protobuf.wrappers_pb2 import StringValue
from rich.tree import Tree
from runconfschema import runconf_services_pb2_grpc
from runconfschema.bootstrap_pb2 import BootRequest
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

from runconf_ui.backend import RunconfContext
from runconf_ui.exceptions import LoggerNotFound, _RunconfUIException
from runconf_ui.state_tree import NodeStatus, State
from runconf_ui.utils import get_logger, init_logger
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


def _ensure_logger(context: RunconfContext) -> None:
    """The TUI logs via the global runconf-ui logger, which RunconfUIBackend normally
    creates. When the server runs in another process nobody has, so make a
    frontend log. (In-process servers have already created one during boot.)"""
    try:
        get_logger()
    except LoggerNotFound:
        log_file = context.output_directory / f"{context.apparatus}_frontend.log"
        init_logger(log_file, context.log_level)


def _session_from_wire(s: str) -> str | Path:
    # Local sessions are config file paths; the TUI displays those by file name.
    return Path(s) if os.path.isabs(s) else s


class RpcBackend:
    """Drop-in replacement for RunconfUIBackend backed by a RunconfService."""

    def __init__(
        self,
        context: RunconfContext,
        address: str,
        timeout: float | None = None,
        frontend_endpoint: str = "",
    ):
        """Connect to the service at ``address`` and boot it with ``context``.

        :param timeout: per-call deadline in seconds (None = wait forever, since
            opening a config or listing remote sessions can be slow)
        """
        self._channel = grpc.insecure_channel(address)
        self._stub = runconf_services_pb2_grpc.RunconfServiceStub(self._channel)
        self._timeout = timeout
        self._lock = threading.Lock()  # TUI workers call in from threads

        self.apparatus = context.apparatus
        self._dropdowns: dict[str, list[str]] = {}
        self._toggles: NodeMap = {}
        self._adjustables: NodeMap = {}
        # Full node state and configuration summary, refetched lazily after changes
        self._groups: list[GroupNodes] | None = None
        self._info: ConfigurationInfo | None = None
        self._session_name: str | None = None
        self._open = False
        self._final_save_path: Path | None = None
        self._closed = False

        boot = BootRequest(
            apparatus=context.apparatus,
            manager_type=context.repo_type.value,
            conf_directory=str(context.conf_directory),
            output_directory=str(context.output_directory),
        )
        boot.frontend_endpoint.url = frontend_endpoint
        for field in ("config_file_name", "base_url", "ops_url"):
            value = getattr(context, field)
            if value:
                setattr(boot, field, value)

        init = self._call(self._stub.boot, boot)
        _ensure_logger(context)
        self._current_version = init.daq_version or None
        self._default_version = init.structure.get("version") or None
        self._update_dropdowns(init.dropdowns)

    # ------------------------------------------------------------------ #
    # Plumbing                                                             #
    # ------------------------------------------------------------------ #

    def _call(self, rpc, request):
        with self._lock:
            reply = rpc(request, timeout=self._timeout)
        response = getattr(reply, "response", None)
        if response is not None and response.outcome == OutcomeFlag.FAIL:
            detail = response.error.message if response.HasField("error") else ""
            raise RpcBackendError(f"{response.message}: {detail}".rstrip(": "))
        return reply

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
        if self._groups is None:
            if not self._open:
                return []
            self._apply_groups(
                self._call(self._stub.get_node_groups, RequestNodeGroups()).groups
            )
        return self._groups  # type: ignore[return-value]

    def _get_info(self) -> ConfigurationInfo:
        if self._info is None:
            self._info = self._call(
                self._stub.get_configuration_info, RequestConfigurationInfo()
            )
            self._session_name = _optional(self._info, "session_name")
        return self._info

    def _set(self, group: NodeGroup, group_id: str, node_id: str, **value) -> None:
        request = RequestSetNodeValue(
            node_group=group, path=[group_id, *node_id.split("__")], **value
        )
        self._merge_nodes(self._call(self._stub.set_node_state, request).nodes)

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
        return self._current_version

    def get_sessions(self) -> list[str | Path]:
        return [_session_from_wire(s) for s in self._dropdowns.get("session", [])]

    def set_daq_version(self, version) -> None:
        self._select("version", version)
        self._current_version = version

    def set_daq_session(self, session: str | Path | None) -> None:
        self._select("session", session)

    def _select(self, key: str, value) -> None:
        reply = self._call(
            self._stub.select_dropdown,
            DropDownSelection(key=key, value="" if value is None else str(value)),
        )
        self._update_dropdowns(reply.update)

    # ------------------------------------------------------------------ #
    # Config lifecycle                                                     #
    # ------------------------------------------------------------------ #

    def open_selected_session(self) -> None:
        reply = self._call(self._stub.open_configuration, Open())
        self._apply_groups(reply.groups)
        self._open = True
        self._info = None
        self._get_info()  # caches session_name for after the server has gone

    def save_config(self) -> None:
        """Save on the server. The service shuts down afterwards (CREATE_QUIT)."""
        reply = self._command(RunconfCommand.CREATE_QUIT)
        path = StringValue()
        if reply.details.Unpack(path):
            self._final_save_path = Path(path.value)
        self._closed = True

    def close(self) -> None:
        """Tell the service to quit without saving (if it hasn't already) and disconnect."""
        if not self._closed:
            try:
                self._command(RunconfCommand.QUIT)
            except grpc.RpcError:
                pass  # server already gone
            self._closed = True
        self._channel.close()

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
    # State                                                                #
    # ------------------------------------------------------------------ #

    def get_excludable_values(self) -> NodeMap:
        return {g: dict(n) for g, n in self._toggles.items()}

    def get_adjustable_values(self) -> NodeMap:
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
