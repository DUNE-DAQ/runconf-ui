"""
Several frontends sharing one server: every frontend sees every other's changes.
The server's repository/conffwk parts are faked (see grpc_fakes.py).
"""

import asyncio
import queue
import threading
from pathlib import Path

import pytest

grpc = pytest.importorskip("grpc")
pytest.importorskip("runconfschema.subscription_pb2")

from grpc_fakes import CONFIG_FILE, FakeBackend  # noqa: E402
from runconfschema import configuration_access_pb2 as ca  # noqa: E402
from runconfschema import main_controls_pb2 as mc  # noqa: E402
from runconfschema import runconf_services_pb2_grpc  # noqa: E402
from runconfschema import state_pb2 as st  # noqa: E402
from runconfschema.subscription_pb2 import RequestSubscribe  # noqa: E402
from textual.widgets import Button  # noqa: E402

from runconf_ui import RepoManagerType, RunconfContext  # noqa: E402
from runconf_ui.api import grpc_service  # noqa: E402
from runconf_ui.api.grpc_client import RpcBackend, RpcBackendError  # noqa: E402
from runconf_ui.textual.runconf_ui_app import RunconfUIApp  # noqa: E402
from runconf_ui.textual.widgets.select_file_panel import (  # noqa: E402
    SessionSelect,
    VersionSelect,
)

APA = ["det", "crp4", "apa1"]


def _context(tmp_path) -> RunconfContext:
    return RunconfContext(
        apparatus="np02",
        conf_directory=Path("/confs"),
        repo_type=RepoManagerType.LOCAL,
        output_directory=tmp_path,
    )


@pytest.fixture
def shared(monkeypatch, tmp_path):
    """A booted server, and a factory for frontends connected to it."""
    monkeypatch.setattr(grpc_service, "RunconfUIBackend", FakeBackend)
    server, service, port = grpc_service.serve("127.0.0.1:0", _context(tmp_path))
    address = f"127.0.0.1:{port}"
    clients: list[RpcBackend] = []

    def connect() -> RpcBackend:
        clients.append(RpcBackend(address, timeout=10, log_dir=tmp_path))
        return clients[-1]

    yield service, address, connect
    for c in clients:
        c.close()
    server.stop(0).wait()


def _changes(client: RpcBackend) -> "queue.Queue":
    q: queue.Queue = queue.Queue()
    client.add_listener(q.put)
    return q


def _next_kind(q: "queue.Queue", kind: str):
    while True:
        change = q.get(timeout=10)
        if change.kind == kind:
            return change


def _open(client: RpcBackend) -> None:
    client.set_daq_version("v1")
    client.set_daq_session(Path(CONFIG_FILE))
    client.open_selected_session()


# ---------------------------------------------------------------------------
# Raw stream
# ---------------------------------------------------------------------------


def test_every_subscriber_gets_the_same_updates(shared):
    _, address, _ = shared
    channels = [grpc.insecure_channel(address) for _ in range(3)]
    stubs = [runconf_services_pb2_grpc.RunconfServiceStub(c) for c in channels]
    try:
        streams = [s.subscribe(RequestSubscribe()) for s in stubs[:2]]
        firsts = [next(s) for s in streams]
        assert all(f.HasField("snapshot") for f in firsts)
        assert not firsts[0].snapshot.config_open
        assert firsts[0].revision == firsts[1].revision

        # The third frontend, which is not subscribed, makes the changes
        actor = stubs[2]
        actor.select_dropdown(ca.DropDownSelection(key="version", value="v1"))
        actor.select_dropdown(ca.DropDownSelection(key="session", value=CONFIG_FILE))
        actor.open_configuration(ca.Open())
        actor.set_node_state(
            st.RequestSetNodeValue(
                node_group=st.TOGGLES, path=APA, node_status_value=st.EXCLUDED
            )
        )

        for stream, first in zip(streams, firsts):
            updates = [next(stream) for _ in range(4)]
            assert [u.revision for u in updates] == [
                first.revision + i for i in range(1, 5)
            ]
            version, session, opened, toggled = updates
            assert version.snapshot.selection == {"version": "v1"}
            assert session.snapshot.selection["session"] == CONFIG_FILE
            assert opened.snapshot.config_open and opened.snapshot.groups
            [node] = [n for n in toggled.nodes.nodes if list(n.node_path) == APA]
            assert node.node_state == st.EXCLUDED

        # Quitting tells every subscriber, then ends their streams
        actor.runconf_command(mc.RunconfCommandRequest(command=mc.QUIT))
        for stream in streams:
            assert next(stream).HasField("shutdown")
            with pytest.raises(StopIteration):
                next(stream)
    finally:
        for c in channels:
            c.close()


def test_replies_carry_the_revision(shared):
    _, address, _ = shared
    with grpc.insecure_channel(address) as channel:
        stub = runconf_services_pb2_grpc.RunconfServiceStub(channel)
        _, call = stub.select_dropdown.with_call(
            ca.DropDownSelection(key="version", value="v1")
        )
        first = int(dict(call.trailing_metadata())[grpc_service.REVISION_KEY])
        _, call = stub.initialise.with_call(ca.RequestInitialisation())
        # A read changes nothing, so the revision stays put
        assert int(dict(call.trailing_metadata())[grpc_service.REVISION_KEY]) == first


def test_subscribe_needs_a_booted_server(monkeypatch):
    monkeypatch.setattr(grpc_service, "RunconfUIBackend", FakeBackend)
    server, _, port = grpc_service.serve("127.0.0.1:0")
    try:
        with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = runconf_services_pb2_grpc.RunconfServiceStub(channel)
            with pytest.raises(grpc.RpcError) as e:
                next(stub.subscribe(RequestSubscribe()))
            assert e.value.code() == grpc.StatusCode.FAILED_PRECONDITION
    finally:
        server.stop(0).wait()


@pytest.mark.asyncio
async def test_server_runs_in_the_callers_event_loop(monkeypatch, tmp_path):
    """run_until_quit_async serves from the running loop until a QUIT arrives."""
    monkeypatch.setattr(grpc_service, "RunconfUIBackend", FakeBackend)
    started: asyncio.Future = asyncio.get_running_loop().create_future()
    task = asyncio.create_task(
        grpc_service.run_until_quit_async(
            "127.0.0.1:0", _context(tmp_path), grace=0, on_started=started.set_result
        )
    )
    port = await asyncio.wait_for(started, 10)
    async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
        stub = runconf_services_pb2_grpc.RunconfServiceStub(channel)
        stream = stub.subscribe(RequestSubscribe())
        first = await stream.read()
        assert first.snapshot.initialisation.apparatus == "np02"
        await stub.runconf_command(mc.RunconfCommandRequest(command=mc.QUIT))
        assert (await stream.read()).HasField("shutdown")
    await asyncio.wait_for(task, 10)  # the server stopped by itself


# ---------------------------------------------------------------------------
# RpcBackend clients
# ---------------------------------------------------------------------------


def test_clients_see_each_others_changes(shared):
    _, _, connect = shared
    alice, bob = connect(), connect()
    alice_changes, bob_changes = _changes(alice), _changes(bob)

    _open(alice)
    _next_kind(bob_changes, "snapshot")
    # Bob's cache follows without him calling anything
    while bob.configuration is None:
        _next_kind(bob_changes, "snapshot")
    assert bob.get_current_version() == "v1"
    assert bob.get_current_session() == Path(CONFIG_FILE)

    alice.toggle("det", "crp4__apa1")
    # Alice's own call returns once her cache includes the change
    assert alice.get_excludable_values()["det"]["crp4__apa1"].node.get() is False
    change = _next_kind(bob_changes, "nodes")
    assert change.revision == alice.revision
    assert bob.get_excludable_values()["det"]["crp4__apa1"].node.get() is False
    # Bob's trees are refetched and show it too
    assert bob.get_tree_views().keys() == alice.get_tree_views().keys()

    bob.set_value("triggers", "crp4__thresh", 12)
    while alice.revision < bob.revision:
        _next_kind(alice_changes, "nodes")
    assert alice.get_adjustable_values()["triggers"]["crp4__thresh"].node.get() == 12


def test_late_client_joins_the_current_state(shared):
    _, _, connect = shared
    alice = connect()
    _open(alice)
    alice.toggle("det", "crp4__apa1")

    late = connect()
    assert late.configuration is not None
    assert late.get_current_version() == "v1"
    assert late.get_excludable_values().keys() == alice.get_excludable_values().keys()
    assert late.get_excludable_values()["det"]["crp4__apa1"].node.get() is False
    assert late.revision == alice.revision


def test_closing_a_client_leaves_the_server_running(shared):
    service, _, connect = shared
    alice, bob = connect(), connect()
    alice.close()
    assert not service.quit_requested.is_set()
    bob.set_daq_version("v2")  # still served
    assert bob.get_current_version() == "v2"


def test_saving_shuts_down_every_client(shared):
    service, _, connect = shared
    alice, bob = connect(), connect()
    bob_changes = _changes(bob)
    _open(alice)
    alice.save_config()

    change = _next_kind(bob_changes, "shutdown")
    assert "saved" in change.message
    assert service.quit_requested.is_set()
    # Bob learns where it was saved, and can do nothing more
    assert bob.final_save_path == Path("/out/cfg.data.xml")
    with pytest.raises(RpcBackendError, match="shut down"):
        bob.set_daq_version("v2")


def test_concurrent_toggles_end_up_consistent(shared):
    """Several users clicking at once: every frontend ends with the server's state."""
    service, _, connect = shared
    clients = [connect() for _ in range(3)]
    _open(clients[0])
    nodes = ["crp4__apa1", "crp4__apa2", "pds"]

    def click(client, node):
        for _ in range(5):
            client.toggle("det", node)

    threads = [
        threading.Thread(target=click, args=(c, n)) for c, n in zip(clients, nodes)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)

    # Sync everyone up to the latest revision with a no-op read
    for c in clients:
        c._call(c._stub.initialise, ca.RequestInitialisation())
    backend = service._backend
    for c in clients:
        for node in nodes:
            assert (
                c.get_excludable_values()["det"][node].node.get()
                == backend.leaf("det", node).get()
                is False  # 5 toggles each, from True
            )


# ---------------------------------------------------------------------------
# The TUI follows other users
# ---------------------------------------------------------------------------


async def _settle(pilot):
    await pilot.app.workers.wait_for_complete()
    await pilot.pause()


async def _until(pilot, condition, tries=50):
    for _ in range(tries):
        if condition():
            return
        await pilot.pause(0.05)
    assert condition()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_tui_shows_another_users_changes(shared):
    service, _, connect = shared
    mine, other = connect(), connect()
    app = RunconfUIApp(mine)  # type: ignore[arg-type]

    async with app.run_test(size=(160, 60)) as pilot:
        await _settle(pilot)  # picks v2 and its only session, and opens it
        await _until(pilot, lambda: app.query("#crp4__apa1"))
        assert app.query_one("#crp4__apa1", Button).has_class("node_included")

        # Someone else excludes a node: our panel follows
        await asyncio.to_thread(other.toggle, "det", "crp4__apa1")
        await _until(
            pilot, lambda: app.query_one("#crp4__apa1", Button).has_class("node_excluded")
        )

        # Someone else picks another version: our dropdowns follow, and we
        # don't echo the selection back to the server
        revision = service._revision
        await asyncio.to_thread(other.set_daq_version, "v1")
        await _until(pilot, lambda: app.query_one(VersionSelect).value == "v1")
        await _settle(pilot)
        assert app.query_one(SessionSelect).is_blank()
        assert service._revision == revision + 1


@pytest.mark.slow
@pytest.mark.asyncio
async def test_tui_joins_without_resetting_others(shared):
    service, _, connect = shared
    other = connect()
    _open(other)  # v1, not the default v2
    other.toggle("det", "crp4__apa1")
    revision = service._revision

    app = RunconfUIApp(connect())  # type: ignore[arg-type]
    async with app.run_test(size=(160, 60)) as pilot:
        await _settle(pilot)
        assert app.query_one(VersionSelect).value == "v1"
        assert app.query_one(SessionSelect).value == Path(CONFIG_FILE)
        await _until(pilot, lambda: app.query("#crp4__apa1"))
        assert app.query_one("#crp4__apa1", Button).has_class("node_excluded")
    # Joining changed nothing on the server
    assert service._revision == revision
    assert service._backend.version == "v1"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_tui_exits_when_another_user_saves(shared):
    _, _, connect = shared
    mine, other = connect(), connect()
    app = RunconfUIApp(mine)  # type: ignore[arg-type]
    exits: list[dict] = []
    async with app.run_test(size=(160, 60)) as pilot:
        await _settle(pilot)
        await _until(pilot, lambda: mine.configuration is not None)
        app.exit = lambda *a, **kw: exits.append(kw)  # type: ignore[method-assign]
        await asyncio.to_thread(other.save_config)
        await _until(pilot, lambda: exits)
    assert "server shut down" in exits[0]["message"]
    # So the exit message can point at the saved config
    assert mine.final_save_path == Path("/out/cfg.data.xml")
