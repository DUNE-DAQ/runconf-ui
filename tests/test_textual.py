"""
Tests for the Textual TUI layer using pytest + pytest-asyncio.
"""

import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

from rich.tree import Tree

from runconf_ui import RunconfContext, RunconfUIBackend
from runconf_ui.state_tree import Group, Leaf, NodeStatus, State
from runconf_ui.textual.runconf_ui_app import RunconfUIApp
from runconf_ui.textual.widgets import (
    AdjustableAttributeTabs,
    ConfigTreePanel,
    EnableDisableTabs,
    FileSelect,
    OptionsPanel,
    RichTreeTabbed,
)
from runconf_ui.textual.widgets.select_file_panel import SessionSelect, VersionSelect
from textual.widgets import Button, Static, TabbedContent

from runconf_ui.textual.screens import (LoadingScreen,
                                        QuitScreen,
                                        CreateScreen,
                                        HelpScreen)


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------


class _StubAdapter:
    def __init__(self, value=True):
        self._value = value
        self._dal_enabled = True

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def dal_enabled(self):
        return self._dal_enabled


def _node(label: str, enabled=True, parent=None):
    state = State.ENABLED if enabled else State.DISABLED
    return NodeStatus(
        node=Leaf(_StubAdapter(enabled), label=label),
        state=state,
        parent=parent,
    )


def _make_backend(
    versions=None,
    sessions=None,
    disableable=None,
    adjustable=None,
    config_loaded=False,
):
    b = MagicMock(spec=RunconfUIBackend)

    b.get_daq_versions.return_value = versions or [
        Path("/fake/v1"),
        Path("/fake/v2"),
    ]

    b.get_current_version.return_value = (versions or [Path("/fake/v1")])[0]

    b.get_sessions.return_value = sessions or [
        Path("/fake/v1/session-a.data.xml"),
        Path("/fake/v1/session-b.data.xml"),
    ]

    b.get_disableable_values.return_value = disableable or {}
    b.get_adjustable_values.return_value = adjustable or {}

    b.get_tree_views.return_value = {}
    b.get_config_tree.return_value = Tree("No Config Loaded")

    b.info_text = "No Config Selected"
    b.configuration = MagicMock() if config_loaded else None

    b.open_selected_session = MagicMock()
    b.save_config = MagicMock()

    return b


def _loaded_backend():
    parent = Group("Readout", strategy=all)

    dis = {
        "Detector": {
            "Readout": NodeStatus(node=parent, state=State.ENABLED, parent=None),
            "Readout__ru-01": _node("ru-01", True, parent),
            "Readout__ru-02": _node("ru-02", True, parent),
        }
    }

    adj = {
        "Random Trigger Rates": {
            "Random Trigger Rates__random-tc-generator - trigger_rate_hz":
                _node("random-tc-generator - trigger_rate_hz", True)
        }
    }

    b = _make_backend(disableable=dis, adjustable=adj, config_loaded=True)

    b.info_text = "DAQ Version: v1\nApparatus: dummy\n"

    b.get_tree_views.return_value = {"Detector": Tree("Detector View")}
    b.get_config_tree.return_value = Tree("dummy-session")

    return b


def _app(backend):
    context = RunconfContext(
        apparatus="dummy",
        conf_directory=Path("/fake"),
        use_local=True,
    )

    app = RunconfUIApp(context)
    app.backend = backend
    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def pilot():
    backend = _make_backend()
    app = _app(backend)

    async with app.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        yield pilot


@pytest_asyncio.fixture
async def loaded_pilot():
    backend = _loaded_backend()
    app = _app(backend)

    async with app.run_test(size=(100, 50)) as pilot:
        app._refresh_enabled_info(load_fresh=True)
        await pilot.pause()
        yield pilot


# ---------------------------------------------------------------------------
# Layout tests
# ---------------------------------------------------------------------------


async def test_main_widgets_present(pilot):
    app = pilot.app

    assert app.query_one(FileSelect)
    assert app.query_one(OptionsPanel)
    assert app.query_one(EnableDisableTabs)
    assert app.query_one(AdjustableAttributeTabs)
    assert app.query_one(ConfigTreePanel)
    assert app.query_one(RichTreeTabbed)


async def test_session_select_disabled_on_startup(pilot):
    assert pilot.app.query_one(SessionSelect).disabled


async def test_open_button_disabled_on_startup(pilot):
    assert pilot.app.query_one("#open_file_button", Button).disabled


async def test_config_buttons_disabled_on_startup(pilot):
    app = pilot.app

    assert app.query_one("#create_run_config", Button).disabled
    assert app.query_one("#reset", Button).disabled


async def test_always_available_buttons_enabled_on_startup(pilot):
    app = pilot.app

    assert not app.query_one("#help", Button).disabled
    assert not app.query_one("#quit", Button).disabled


# ---------------------------------------------------------------------------
# File select flow
# ---------------------------------------------------------------------------


async def test_selecting_version_enables_session_select(pilot):
    app = pilot.app
    backend = app.backend

    app.query_one(VersionSelect).value = backend.get_daq_versions()[0]

    await pilot.pause()

    assert not app.query_one(SessionSelect).disabled


async def test_selecting_session_enables_open_button(pilot):
    app = pilot.app
    backend = app.backend

    app.query_one(VersionSelect).value = backend.get_daq_versions()[0]
    await pilot.pause()

    app.query_one(SessionSelect).value = backend.get_sessions()[0]
    await pilot.pause()

    assert not app.query_one("#open_file_button", Button).disabled


async def test_open_button_pushes_loading_screen():
    backend = _make_backend()

    with patch.object(RunconfUIApp, "_load_config_worker"):
        async with _app(backend).run_test(size=(100, 50)) as pilot:

            app = pilot.app

            app.query_one(VersionSelect).value = backend.get_daq_versions()[0]
            await pilot.pause()

            app.query_one(SessionSelect).value = backend.get_sessions()[0]
            await pilot.pause()

            await pilot.click("#open_file_button")
            await pilot.pause()

            assert isinstance(app.screen, LoadingScreen)


# ---------------------------------------------------------------------------
# Options panel
# ---------------------------------------------------------------------------


async def test_quit_opens_quit_screen(pilot):
    await pilot.click("#quit")
    await pilot.pause()

    assert isinstance(pilot.app.screen, QuitScreen)


async def test_help_opens_help_screen(pilot):
    await pilot.click("#help")
    await pilot.pause()

    assert isinstance(pilot.app.screen, HelpScreen)


async def test_create_enabled_after_load(loaded_pilot):
    app = loaded_pilot.app
    assert not app.query_one("#create_run_config", Button).disabled


async def test_create_opens_screen(loaded_pilot):
    await loaded_pilot.click("#create_run_config")
    await loaded_pilot.pause()
    assert isinstance(loaded_pilot.app.screen, CreateScreen)


# ---------------------------------------------------------------------------
# Quit screen
# ---------------------------------------------------------------------------


async def test_cancel_pops_quit_screen(pilot):
    await pilot.click("#quit")
    await pilot.pause()

    await pilot.click("#cancel_button")
    await pilot.pause()

    assert not isinstance(pilot.app.screen, QuitScreen)


async def test_quit_scrap_exits_app(pilot):
    await pilot.click("#quit")
    await pilot.pause()

    await pilot.click("#quit_scrap_button")
    await pilot.pause()

    assert not pilot.app.is_running


# ---------------------------------------------------------------------------
# Enable/Disable panel
# ---------------------------------------------------------------------------


async def test_buttons_render_after_load(loaded_pilot):
    buttons = list(loaded_pilot.app.query(".enable_disable_button"))

    assert len(buttons) > 0


async def test_enabled_node_has_class(loaded_pilot):
    button = loaded_pilot.app.query_one("#Readout", Button)

    assert "node_enabled" in button.classes


async def test_clicking_button_calls_backend_toggle():
    backend = _loaded_backend()

    async with _app(backend).run_test(size=(100, 50)) as pilot:

        app = pilot.app

        app._refresh_enabled_info(load_fresh=True)
        await pilot.pause()

        await pilot.click("#Readout")
        await pilot.pause()

        backend.toggle.assert_called_once_with("Detector", "Readout")


# ---------------------------------------------------------------------------
# Post-load UI state
# ---------------------------------------------------------------------------


async def test_option_buttons_enabled_after_load(loaded_pilot):
    app = loaded_pilot.app

    for btn in ("create_run_config", "help", "reset", "quit"):
        assert not app.query_one(f"#{btn}", Button).disabled


async def test_config_info_text_updated_after_load(loaded_pilot):
    info = loaded_pilot.app.query_one("#config_info", Static)

    assert "No Config Loaded" not in str(info.renderable)


async def test_adjustable_tabs_have_content(loaded_pilot):
    tabbed = (
        loaded_pilot.app
        .query_one(AdjustableAttributeTabs)
        .query_one(TabbedContent)
    )

    assert tabbed.tab_count >= 1


