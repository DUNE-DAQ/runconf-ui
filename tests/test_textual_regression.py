"""
Static regression tests — Textual version migration guards.

These are synchronous checks that require no running app. They protect against
the patterns that caused silent failures when migrating from Textual 0.87.x to 7.x:

  - MainScreen as ModalScreen breaks app.query() — it mounts on top of _default,
    so queries search the wrong (empty) screen.
  - SCREENS + push_screen() has the same problem — stacks on _default.
  - switch_mode() in on_mount races against run_test in Textual 7.x.
    DEFAULT_MODE is resolved at class definition time, before the event loop.
"""

from textual.screen import ModalScreen, Screen

from runconf_ui.textual.runconf_ui_app import RunconfUIApp
from runconf_ui.textual.screens import (
    CreateScreen,
    HelpScreen,
    LoadingScreen,
    MainScreen,
    QuitScreen,
)


def test_main_screen_is_not_modal():
    """MainScreen must be a plain Screen, not ModalScreen.

    ModalScreen has a different mounting lifecycle and sits on top of _default,
    causing app.query() to search the wrong screen in Textual 7.x.
    """
    assert not issubclass(MainScreen, ModalScreen), (
        "MainScreen must not be a ModalScreen — use textual.screen.Screen instead. "
        "ModalScreen breaks app.query() in Textual 7.x."
    )


def test_main_screen_is_screen():
    assert issubclass(MainScreen, Screen)


def test_overlay_screens_are_screens():
    for screen_cls in (QuitScreen, CreateScreen, HelpScreen, LoadingScreen):
        assert issubclass(screen_cls, Screen), (
            f"{screen_cls.__name__} must be a Screen subclass"
        )


def test_main_screen_registered_in_modes():
    """MainScreen must be in MODES not SCREENS.

    In Textual 7.x, SCREENS + push_screen() stacks on _default so app.query()
    finds nothing. MODES + DEFAULT_MODE activates before the event loop starts.
    """
    assert "main" in RunconfUIApp.MODES, (
        "MainScreen must be in MODES. "
        "SCREENS + push_screen() stacks on _default and breaks app.query() in Textual 7.x."
    )
    assert RunconfUIApp.MODES["main"] is MainScreen


def test_main_screen_not_in_screens():
    """MainScreen must not also be in SCREENS — that re-enables push_screen('main')
    which reverts to the broken _default stacking behaviour."""
    assert "main" not in RunconfUIApp.SCREENS, (
        "MainScreen must not be in SCREENS — push_screen('main') stacks on _default."
    )


def test_default_mode_is_main():
    """DEFAULT_MODE must be 'main'.

    switch_mode() in on_mount races against run_test in Textual 7.x.
    DEFAULT_MODE is resolved at class definition time, before the event loop.
    """
    assert getattr(RunconfUIApp, "DEFAULT_MODE", None) == "main", (
        "DEFAULT_MODE must be 'main'. "
        "switch_mode() in on_mount races against run_test in Textual 7.x."
    )


def test_overlay_screens_registered_in_screens():
    """Overlay screens must be in SCREENS so push_screen() can find them."""
    for name, cls in (
        ("create", CreateScreen),
        ("quit", QuitScreen),
        ("load", LoadingScreen),
        ("help", HelpScreen),
    ):
        assert name in RunconfUIApp.SCREENS, (
            f"'{name}' must be in SCREENS for push_screen() to work."
        )
        assert RunconfUIApp.SCREENS[name] is cls
