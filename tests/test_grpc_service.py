"""
End-to-end tests for the gRPC layer over a real in-process channel.
The backend's repository/conffwk parts are faked (see grpc_fakes.py); node state
and tree building run through the real backend code.
"""

import pytest

grpc = pytest.importorskip("grpc")
pytest.importorskip("runconfschema.runconf_services_pb2_grpc")

import io  # noqa: E402
from pathlib import Path  # noqa: E402

from google.protobuf.wrappers_pb2 import StringValue  # noqa: E402
from grpc_fakes import CONFIG_FILE, SESSION_NAME, FakeBackend  # noqa: E402
from rich.console import Console  # noqa: E402
from runconfschema import bootstrap_pb2, runconf_services_pb2_grpc  # noqa: E402
from runconfschema import configuration_access_pb2 as ca  # noqa: E402
from runconfschema import main_controls_pb2 as mc  # noqa: E402
from runconfschema import state_pb2 as st  # noqa: E402
from runconfschema.common_pb2 import OutcomeFlag  # noqa: E402

from runconf_ui import RepoManagerType, RunconfContext  # noqa: E402
from runconf_ui.api import grpc_service  # noqa: E402
from runconf_ui.api.grpc_client import RpcBackend, RpcBackendError  # noqa: E402

APA = ["det", "crp4", "apa1"]
THRESH = ["triggers", "crp4", "thresh"]


@pytest.fixture
def served(monkeypatch):
    monkeypatch.setattr(grpc_service, "RunconfUIBackend", FakeBackend)
    server, service, port = grpc_service.serve("127.0.0.1:0")
    yield service, f"127.0.0.1:{port}"
    server.stop(0)


@pytest.fixture
def rpc(served):
    service, address = served
    channel = grpc.insecure_channel(address)
    yield runconf_services_pb2_grpc.RunconfServiceStub(channel), service
    channel.close()


def _boot(stub, **kw):
    return stub.boot(
        bootstrap_pb2.BootRequest(
            apparatus="np02", manager_type="local", conf_directory="/x", **kw
        )
    )


def _open(stub, boot=True):
    if boot:
        _boot(stub)
    stub.select_dropdown(ca.DropDownSelection(key="version", value="v1"))
    stub.select_dropdown(ca.DropDownSelection(key="session", value=CONFIG_FILE))
    return stub.open_configuration(ca.Open())


def _text(renderable) -> str:
    console = Console(
        file=io.StringIO(), width=120, record=True, color_system="truecolor"
    )
    console.print(renderable)
    return console.export_text(styles=True)


# ---------------------------------------------------------------------------
# Raw service
# ---------------------------------------------------------------------------


def test_calls_before_boot_are_rejected(rpc):
    stub, _ = rpc
    with pytest.raises(grpc.RpcError) as e:
        stub.select_dropdown(ca.DropDownSelection(key="version", value="v2"))
    assert e.value.code() == grpc.StatusCode.FAILED_PRECONDITION


def test_boot_returns_dropdowns_and_maps_optionals(rpc):
    stub, service = rpc
    init = _boot(stub, config_file_name="default.data.xml")
    assert init.apparatus == "np02"
    assert list(init.dropdowns["version"].values) == ["v1", "v2"]
    assert init.structure["version"] == "v2"
    ctx = service._backend.ctx
    assert ctx.config_file_name == "default.data.xml"
    assert ctx.base_url is None and ctx.ops_url is None


def test_select_dropdown_maps_strings_back_to_backend_objects(rpc):
    stub, service = rpc
    _boot(stub)
    upd = stub.select_dropdown(ca.DropDownSelection(key="version", value="v1"))
    assert upd.response.outcome == OutcomeFlag.SUCCESS
    assert list(upd.resets) == ["session"]
    assert list(upd.update["session"].values) == [CONFIG_FILE]

    stub.select_dropdown(ca.DropDownSelection(key="session", value=CONFIG_FILE))
    assert service._backend.session == Path(CONFIG_FILE)  # the Path, not the string

    bad = stub.select_dropdown(ca.DropDownSelection(key="session", value="nope"))
    assert bad.response.outcome == OutcomeFlag.FAIL
    bad = stub.select_dropdown(ca.DropDownSelection(key="nope", value="x"))
    assert bad.response.outcome == OutcomeFlag.FAIL


def test_node_calls_need_open_config(rpc):
    stub, _ = rpc
    _boot(stub)
    with pytest.raises(grpc.RpcError) as e:
        stub.get_node_state(st.RequestNodeStatus(path=APA))
    assert e.value.code() == grpc.StatusCode.FAILED_PRECONDITION


def test_open_returns_groups_with_flat_nodes_and_hierarchy(rpc):
    stub, _ = rpc
    out = _open(stub)
    assert out.response.outcome == OutcomeFlag.SUCCESS
    groups = {g.group_id: g for g in out.groups}
    assert [g.node_group for g in out.groups] == [st.TOGGLES, st.ADJUSTABLE]

    det = groups["det"]
    assert det.view_panel == "Det map"
    assert not groups["triggers"].HasField("view_panel")

    flat = {tuple(n.node_path): n for n in det.nodes}
    apa = flat[tuple(APA)]
    assert apa.label == "apa1" and apa.tooltip == "APA 1" and apa.bool_value is True
    # node in an unlabelled group is addressed by its label alone
    assert ("det", "pds") in flat
    assert flat[("det", "crp5", "apa3")].node_state == st.PARENT_EXCLUDED

    # Hierarchy: system root (not addressable) -> crp4/crp5/pds (unlabelled group flattened)
    (root,) = det.systems
    assert root.label == "np02" and list(root.node_path) == []
    # Groups sort before leaves, so the flattened unlabelled group's leaf comes first
    labels = [c.label for c in root.children]
    assert labels == ["pds", "crp4", "crp5"]
    crp4 = root.children[1]
    assert list(crp4.node_path) == ["det", "np02", "crp4"]
    assert list(crp4.children[0].node_path) == APA

    thresh = {tuple(n.node_path): n for n in groups["triggers"].nodes}[tuple(THRESH)]
    assert thresh.WhichOneof("value") == "int_value" and thresh.int_value == 10


def test_get_and_set_node_state(rpc):
    stub, service = rpc
    _open(stub)
    got = stub.get_node_state(
        st.RequestNodeStatus(node_group=st.ADJUSTABLE, path=THRESH)
    )
    assert got.nodes[0].int_value == 10

    changed = stub.set_node_state(
        st.RequestSetNodeValue(
            node_group=st.TOGGLES, path=APA, node_status_value=st.EXCLUDED
        )
    )
    assert changed.response.outcome == OutcomeFlag.SUCCESS
    assert [(list(n.node_path), n.node_state) for n in changed.nodes] == [
        (APA, st.EXCLUDED)
    ]
    assert service._backend.leaf("det", "crp4__apa1").get() is False

    # Strings are passed through untouched, as the TUI does today
    stub.set_node_state(
        st.RequestSetNodeValue(node_group=st.ADJUSTABLE, path=THRESH, string_value="12")
    )
    assert service._backend.leaf("triggers", "crp4__thresh").get() == "12"

    bad = stub.set_node_state(
        st.RequestSetNodeValue(node_group=st.ADJUSTABLE, path=["x", "y"], int_value=1)
    )
    assert bad.response.outcome == OutcomeFlag.FAIL


def test_get_node_groups_reflects_changes(rpc):
    stub, _ = rpc
    _open(stub)
    done = stub.set_node_state(
        st.RequestSetNodeValue(node_group=st.TOGGLES, path=APA, bool_value=False)
    )
    assert done.response.outcome == OutcomeFlag.SUCCESS
    groups = stub.get_node_groups(st.RequestNodeGroups()).groups
    crp4 = groups[0].systems[0].children[1]
    apa = crp4.children[0]
    assert apa.label == "apa1" and apa.node_state == st.EXCLUDED


def test_get_configuration_info(rpc):
    stub, _ = rpc
    _boot(stub)
    closed = stub.get_configuration_info(ca.RequestConfigurationInfo())
    assert not closed.config_open and not closed.HasField("session_name")

    _open(stub, boot=False)
    info = stub.get_configuration_info(ca.RequestConfigurationInfo())
    assert info.config_open and info.session_name == SESSION_NAME
    assert info.config_file == CONFIG_FILE and info.daq_version == "v1"
    (segment,) = info.config_tree
    assert segment.label == "segment" and not segment.HasField("state")
    assert segment.children[0].state == st.INCLUDED


def test_command_help_and_quit_without_boot(rpc):
    stub, service = rpc
    help_ = stub.runconf_command(mc.RunconfCommandRequest(command=mc.HELP))
    text = StringValue()
    assert help_.details.Unpack(text) and "runconf_command" in text.value

    stub.runconf_command(mc.RunconfCommandRequest(command=mc.QUIT))
    assert service.quit_requested.is_set()


def test_command_create_quit_saves(rpc):
    stub, service = rpc
    _boot(stub)
    early = stub.runconf_command(mc.RunconfCommandRequest(command=mc.CREATE_QUIT))
    assert early.response.outcome == OutcomeFlag.FAIL
    assert not service.quit_requested.is_set()

    _open(stub, boot=False)
    out = stub.runconf_command(mc.RunconfCommandRequest(command=mc.CREATE_QUIT))
    path = StringValue()
    assert out.details.Unpack(path) and path.value == "/out/cfg.data.xml"
    assert service._backend.saved and service.quit_requested.is_set()


def test_command_reset_returns_groups(rpc):
    stub, _ = rpc
    _open(stub)
    out = stub.runconf_command(mc.RunconfCommandRequest(command=mc.RESET))
    state = ca.ConfigurationOutcome()
    assert out.details.Unpack(state) and len(state.groups) == 2


# ---------------------------------------------------------------------------
# Client renders exactly what the backend would have rendered
# ---------------------------------------------------------------------------


def _context(tmp_path):
    return RunconfContext(
        apparatus="np02",
        conf_directory=Path("/confs"),
        repo_type=RepoManagerType.LOCAL,
        output_directory=tmp_path,
    )


@pytest.fixture
def self_booted(monkeypatch, tmp_path):
    """A server booted with its own context, as runconf-ui-server -a ... does."""
    monkeypatch.setattr(grpc_service, "RunconfUIBackend", FakeBackend)
    server, service, port = grpc_service.serve("127.0.0.1:0", _context(tmp_path))
    yield service, f"127.0.0.1:{port}"
    server.stop(0)


def test_boot_only_once(rpc):
    stub, service = rpc
    _boot(stub)
    first = service._backend
    with pytest.raises(grpc.RpcError) as e:
        _boot(stub)
    assert e.value.code() == grpc.StatusCode.ALREADY_EXISTS
    assert service._backend is first


def test_initialise_needs_a_booted_server(rpc):
    stub, _ = rpc
    with pytest.raises(grpc.RpcError) as e:
        stub.initialise(ca.RequestInitialisation())
    assert e.value.code() == grpc.StatusCode.FAILED_PRECONDITION


def test_frontends_share_the_server_context(self_booted, tmp_path):
    service, address = self_booted
    assert service._backend.ctx.apparatus == "np02"
    # Frontends need no context and see the same state, including each
    # other's selections (the basis for one server shared by many users later)
    clients = []

    def connect():
        clients.append(RpcBackend(address, timeout=10, log_dir=tmp_path))
        return clients[-1]

    try:
        first, second = connect(), connect()
        assert first.apparatus == second.apparatus == "np02"
        assert first.get_default_version() == "v2"
        first.set_daq_version("v1")
        late = connect()
        assert late.get_current_version() == "v1"
        assert [str(s) for s in late.get_sessions()] == [CONFIG_FILE]
    finally:
        for c in clients:
            c.close()  # disconnects only: the shared server keeps running


def test_client_rendering_matches_backend(self_booted, tmp_path):
    service, address = self_booted
    client = RpcBackend(address, timeout=10, log_dir=tmp_path)
    try:
        assert client.info_text == "No Config Selected"
        assert _text(client.get_config_tree()).strip() == "No Config Loaded"

        client.set_daq_version("v1")
        client.set_daq_session(client.get_sessions()[0])
        client.open_selected_session()
        backend = service._backend

        def check():
            assert client.info_text == backend.info_text
            assert _text(client.get_config_tree()) == _text(backend.get_config_tree())
            remote, local = client.get_tree_views(), backend.get_tree_views()
            assert list(remote) == list(local) == ["det"]
            assert _text(remote["det"]) == _text(local["det"])
            for mine, theirs in (
                (client.get_excludable_values(), backend.get_excludable_values()),
                (client.get_adjustable_values(), backend.get_adjustable_values()),
            ):
                assert {g: list(n) for g, n in mine.items()} == {
                    g: list(n) for g, n in theirs.items()
                }
                for g, nodes in theirs.items():
                    for node_id, status in nodes.items():
                        remote_status = mine[g][node_id]
                        assert remote_status.state == status.state
                        assert remote_status.value == status.value
                        assert remote_status.path == status.path

        check()
        client.toggle("det", "crp4__apa1")
        client.set_value("triggers", "crp4__thresh", "42")
        check()
        assert "excluded" in _text(client.get_tree_views()["det"])
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Connecting and starting
# ---------------------------------------------------------------------------


def test_client_explains_unbooted_server(served, tmp_path):
    _, address = served  # no context, no boot RPC
    with pytest.raises(RpcBackendError, match="not been booted"):
        RpcBackend(address, timeout=10, log_dir=tmp_path)


def test_client_explains_missing_server(tmp_path):
    server, _, port = grpc_service.serve("127.0.0.1:0")
    server.stop(0).wait()  # nothing listening on this port any more
    with pytest.raises(RpcBackendError, match="No runconf-ui server is reachable"):
        RpcBackend(f"127.0.0.1:{port}", timeout=10, log_dir=tmp_path)


def test_server_cli_requires_an_apparatus():
    from click.testing import CliRunner

    from runconf_ui.apps.runconf_ui_main import server_cli

    result = CliRunner().invoke(
        server_cli, ["-g", "127.0.0.1:0"], env={"APPARATUS": None}
    )
    assert result.exit_code == 2  # click usage error, not a server waiting forever
    assert "Apparatus must be specified" in result.output
