"""
Drive the real Textual app through RpcBackend -> gRPC -> RunconfService.
Only the server-side RunconfUIBackend is faked (see grpc_fakes.py).
"""

from pathlib import Path

import pytest

pytest.importorskip("grpc")
pytest.importorskip("runconfschema.runconf_services_pb2_grpc")

from grpc_fakes import FakeBackend
from textual.widgets import Button, Input, Static

from runconf_ui import RepoManagerType, RunconfContext
from runconf_ui.api import grpc_service
from runconf_ui.api.grpc_client import RpcBackend
from runconf_ui.apps.runconf_ui_main import get_exit_msg
from runconf_ui.textual import messages as runconf_msg
from runconf_ui.textual.runconf_ui_app import RunconfUIApp
from runconf_ui.textual.screens import ExceptionScreen
from runconf_ui.textual.widgets import (
    ConfigTreePanel,
    RichTreeTabbed,
)
from runconf_ui.textual.widgets.adjustable_attribute_panel import (
    AdjustableAttributeContainer,
)
from runconf_ui.textual.widgets.select_file_panel import (
    SessionSelect,
    VersionSelect,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def served(monkeypatch, tmp_path):
    monkeypatch.setattr(grpc_service, "RunconfUIBackend", FakeBackend)
    FakeBackend.instances.clear()
    ctx = RunconfContext(
        apparatus="np02",
        conf_directory=Path("/confs"),
        repo_type=RepoManagerType.LOCAL,
        output_directory=tmp_path,
    )
    # The server is booted with the shared context; the frontend only connects
    server, service, port = grpc_service.serve("127.0.0.1:0", ctx)
    client = RpcBackend(f"127.0.0.1:{port}", timeout=10, log_dir=tmp_path)
    yield client, service
    client.close()
    server.stop(0)


async def _settle(pilot):
    await pilot.app.workers.wait_for_complete()
    await pilot.pause()


async def _open_config(pilot):
    """Startup selects the default version (v2); with a single session the TUI
    selects it and opens the config by itself."""
    app = pilot.app
    await _settle(pilot)
    assert app.query_one(VersionSelect).value == "v2"
    session_select = app.query_one(SessionSelect)
    # Path sessions come back as Paths, so the TUI shows the file name
    assert [label for label, _ in session_select._options[1:]] == ["np02.data.xml"]
    assert session_select.value == Path("/confs/np02.data.xml")
    await _settle(pilot)


@pytest.mark.slow
async def test_tui_full_flow_over_grpc(served):
    client, service = served
    app = RunconfUIApp(client)  # type: ignore[arg-type]

    async with app.run_test(size=(160, 60)) as pilot:
        await _open_config(pilot)
        server_backend = service._backend
        assert server_backend.version == "v2"
        assert server_backend.session == Path("/confs/np02.data.xml")
        assert server_backend.configuration is not None

        # Info text and trees are drawn locally from structured data
        assert "np02.data.xml" in str(app.query_one("#config_info", Static).render())
        assert app.query(ConfigTreePanel) and app.query(RichTreeTabbed)

        # Toggle a node from the include/exclude panel
        button = app.query_one("#crp4__apa1", Button)
        assert button.has_class("node_included")
        button.press()
        await _settle(pilot)
        assert server_backend.leaf("det", "crp4__apa1").get() is False
        assert app.query_one("#crp4__apa1", Button).has_class("node_excluded")

        # Change an adjustable value: raw input text goes through unchanged
        container = app.query_one(AdjustableAttributeContainer)
        container.query_one(Input).value = "42"
        container.query_one("#apply", Button).press()
        await _settle(pilot)
        assert server_backend.leaf("triggers", "crp4__thresh").get() == "42"

        # Quit and save -> CREATE_QUIT on the server
        app.post_message(runconf_msg.QuitAndSaveMessage())
        await pilot.pause()

    assert server_backend.saved and service.quit_requested.is_set()
    assert client.final_save_path == Path("/out/cfg.data.xml")
    assert client.config_session.id == "np02-session"
    # The file doesn't exist on this machine, so the exit message says so
    assert "not created" in get_exit_msg(client)  # type: ignore[arg-type]


@pytest.mark.slow
async def test_tui_shows_server_failure_as_popup(served, monkeypatch):
    client, _ = served

    def broken_open(self):
        raise ValueError("repo is broken")

    monkeypatch.setattr(FakeBackend, "open_selected_session", broken_open)
    app = RunconfUIApp(client)  # type: ignore[arg-type]

    async with app.run_test(size=(160, 60)) as pilot:
        await _settle(pilot)  # auto-open fails on the server
        assert isinstance(app.screen, ExceptionScreen)
        assert any(
            "repo is broken" in str(s.render()) for s in app.screen.query(Static)
        )
        assert client.configuration is None
