"""
Tests for the Textual TUI layer using pytest + pytest-asyncio.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from rich.tree import Tree
from textual.widgets import Button, Select, Static, TabbedContent

from runconf_ui import RunconfContext, RunconfUIBackend
from runconf_ui.state_tree import Group, Leaf, NodeStatus, State
from runconf_ui.textual.runconf_ui_app import RunconfUIApp
from runconf_ui.textual.screens import (
    CreateScreen,
    HelpScreen,
    LoadingScreen,
    MainScreen,
    QuitScreen,
)
from runconf_ui.textual.widgets import (
    AdjustableAttributeTabs,
    ConfigTreePanel,
    EnableDisableTabs,
    FileSelect,
    OptionsPanel,
    RichTreeTabbed,
)
from runconf_ui.textual.widgets.select_file_panel import SessionSelect, VersionSelect

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
        node=Leaf(_StubAdapter(enabled), label=label),  # type: ignore
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
            "Random Trigger Rates__random-tc-generator - trigger_rate_hz": _node(
                "random-tc-generator - trigger_rate_hz", True
            )
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


def _first_real_option_value(select_widget):
    """Return the value of the first non-blank option in a Select widget.

    In Textual 7.x, _options is a list of (label, value) tuples and the
    blank sentinel is stored as Select.BLANK. Skip it to get a real value.
    """
    for _label, value in select_widget._options:
        if value is not Select.BLANK:
            return value
    raise ValueError("No non-blank options found in Select widget")


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
# Regression tests — runtime checks (static checks are in test_textual_regression.py)
# ---------------------------------------------------------------------------


@pytest.mark.slow
async def test_active_screen_is_main_screen_on_startup(pilot):
    """The active screen immediately after startup must be MainScreen, not _default."""
    assert isinstance(pilot.app.screen, MainScreen), (
        f"Expected MainScreen, got {type(pilot.app.screen)}. "
        "MainScreen is not the active screen — check MODES and DEFAULT_MODE."
    )


@pytest.mark.slow
async def test_active_screen_id_is_not_default(pilot):
    """If screen id is '_default', MainScreen was never made active."""
    assert pilot.app.screen.id != "_default", (
        "Active screen is '_default' — MainScreen was never activated. "
        "This is the Textual 7.x push_screen regression."
    )


@pytest.mark.slow
async def test_app_query_reaches_main_screen_widgets(pilot):
    """app.query() must find MainScreen widgets directly.

    This is the core regression: in the broken configuration, app.query()
    searches _default (empty) instead of MainScreen.
    """
    assert list(pilot.app.query(FileSelect)), (
        "app.query(FileSelect) found nothing — MainScreen is not the active base screen. "
        "Check MODES and DEFAULT_MODE on RunconfUIApp."
    )


# ---------------------------------------------------------------------------
# Layout tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
async def test_main_widgets_present(pilot):
    app = pilot.app

    assert app.query_one(FileSelect)
    assert app.query_one(OptionsPanel)
    assert app.query_one(EnableDisableTabs)
    assert app.query_one(AdjustableAttributeTabs)
    assert app.query_one(ConfigTreePanel)
    assert app.query_one(RichTreeTabbed)


@pytest.mark.slow
async def test_session_select_disabled_on_startup(pilot):
    assert pilot.app.query_one(SessionSelect).disabled


@pytest.mark.slow
async def test_open_button_disabled_on_startup(pilot):
    assert pilot.app.query_one("#open_file_button", Button).disabled


@pytest.mark.slow
async def test_config_buttons_disabled_on_startup(pilot):
    app = pilot.app

    assert app.query_one("#create_run_config", Button).disabled
    assert app.query_one("#reset", Button).disabled


@pytest.mark.slow
async def test_always_available_buttons_enabled_on_startup(pilot):
    app = pilot.app

    assert not app.query_one("#help", Button).disabled
    assert not app.query_one("#quit", Button).disabled


# ---------------------------------------------------------------------------
# File select flow
# ---------------------------------------------------------------------------


@pytest.mark.slow
async def test_selecting_version_enables_session_select(pilot):
    app = pilot.app

    # Extra pause to let call_after_refresh(_init_file_selects) populate options.
    # In Textual 7.x _options is [(label, value), ...] with Select.BLANK first.
    await pilot.pause()
    version_select = app.query_one(VersionSelect)
    version_select.value = _first_real_option_value(version_select)
    await pilot.pause()

    assert not app.query_one(SessionSelect).disabled


@pytest.mark.slow
async def test_selecting_session_enables_open_button(pilot):
    app = pilot.app

    await pilot.pause()
    version_select = app.query_one(VersionSelect)
    version_select.value = _first_real_option_value(version_select)
    await pilot.pause()

    session_select = app.query_one(SessionSelect)
    session_select.value = _first_real_option_value(session_select)
    await pilot.pause()

    assert not app.query_one("#open_file_button", Button).disabled


@pytest.mark.slow
async def test_open_button_pushes_loading_screen():
    backend = _make_backend()

    with patch.object(RunconfUIApp, "_load_config_worker"):
        async with _app(backend).run_test(size=(100, 50)) as pilot:
            app = pilot.app

            await pilot.pause()
            version_select = app.query_one(VersionSelect)
            version_select.value = _first_real_option_value(version_select)
            await pilot.pause()

            session_select = app.query_one(SessionSelect)
            session_select.value = _first_real_option_value(session_select)
            await pilot.pause()

            await pilot.click("#open_file_button")
            await pilot.pause()

            assert isinstance(app.screen, LoadingScreen)


# ---------------------------------------------------------------------------
# Options panel
# ---------------------------------------------------------------------------


@pytest.mark.slow
async def test_quit_opens_quit_screen(pilot):
    await pilot.click("#quit")
    await pilot.pause()

    assert isinstance(pilot.app.screen, QuitScreen)


@pytest.mark.slow
async def test_help_opens_help_screen(pilot):
    await pilot.click("#help")
    await pilot.pause()

    assert isinstance(pilot.app.screen, HelpScreen)


@pytest.mark.slow
async def test_create_enabled_after_load(loaded_pilot):
    app = loaded_pilot.app
    assert not app.query_one("#create_run_config", Button).disabled


@pytest.mark.slow
async def test_create_opens_screen(loaded_pilot):
    await loaded_pilot.click("#create_run_config")
    await loaded_pilot.pause()
    assert isinstance(loaded_pilot.app.screen, CreateScreen)


# ---------------------------------------------------------------------------
# Quit screen
# ---------------------------------------------------------------------------


@pytest.mark.slow
async def test_cancel_pops_quit_screen(pilot):
    await pilot.click("#quit")
    await pilot.pause()

    await pilot.click("#cancel_button")
    await pilot.pause()

    assert not isinstance(pilot.app.screen, QuitScreen)


@pytest.mark.slow
async def test_quit_scrap_exits_app(pilot):
    await pilot.click("#quit")
    await pilot.pause()

    await pilot.click("#quit_scrap_button")
    await pilot.pause()

    assert not pilot.app.is_running


# ---------------------------------------------------------------------------
# Enable/Disable panel
# ---------------------------------------------------------------------------


@pytest.mark.slow
async def test_buttons_render_after_load(loaded_pilot):
    buttons = list(loaded_pilot.app.query(".main_enabled_btn")) + list(
        loaded_pilot.app.query(".sub_enabled_btn")
    )

    assert len(buttons) > 0


@pytest.mark.slow
async def test_enabled_node_has_class(loaded_pilot):
    button = loaded_pilot.app.query_one("#Readout", Button)

    assert "node_enabled" in button.classes


@pytest.mark.slow
async def test_clicking_button_calls_backend_toggle():
    backend = _loaded_backend()

    async with _app(backend).run_test(size=(100, 50)) as pilot:
        app = pilot.app

        app._refresh_enabled_info(load_fresh=True)
        await pilot.pause()

        # In Textual 7.x, buttons inside TabbedContent don't receive click
        # events unless their tab is focused. Post the message directly to
        # test that the handler wires through to backend.toggle correctly.
        from runconf_ui.textual import messages as runconf_msg

        app.post_message(
            runconf_msg.NodeToggledMessage(
                group_id="Detector",
                widget_id="Readout",
            )
        )
        await pilot.pause()

        backend.toggle.assert_called_once_with("Detector", "Readout")


# ---------------------------------------------------------------------------
# Post-load UI state
# ---------------------------------------------------------------------------


@pytest.mark.slow
async def test_option_buttons_enabled_after_load(loaded_pilot):
    app = loaded_pilot.app

    for btn in ("create_run_config", "help", "reset", "quit"):
        assert not app.query_one(f"#{btn}", Button).disabled


@pytest.mark.slow
async def test_config_info_text_updated_after_load(loaded_pilot):
    info = loaded_pilot.app.query_one("#config_info", Static)

    # In Textual 7.x, Static uses .content not .renderable
    assert "No Config Loaded" not in str(info.content)


@pytest.mark.slow
async def test_adjustable_tabs_have_content(loaded_pilot):
    tabbed = loaded_pilot.app.query_one(AdjustableAttributeTabs).query_one(
        TabbedContent
    )

    assert tabbed.tab_count >= 1
