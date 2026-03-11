"""
Textual application for controlling runconf-shifter-ui.
"""
from importlib.metadata import version
from typing import ClassVar

from textual import on, work
from textual.app import App

from runconf_ui.backend import RunconfContext, RunconfUIBackend
from runconf_ui.textual import messages as runconf_msg
from runconf_ui.textual.screens import CreateScreen, HelpScreen, MainScreen, QuitScreen
from runconf_ui.textual.screens.popup_screens import LoadingScreen
from runconf_ui.textual.widgets import (
    AdjustableAttributeTabs,
    ConfigTreePanel,
    EnableDisableTabs,
    FileSelect,
    OptionsPanel,
    RichTreeTabbed,
)

class RunconfUIApp(App):
    CSS_PATH: ClassVar[str] = "runconf_shifter_ui.tcss"
    BINDINGS: ClassVar[list[tuple]] = [("ctrl+q", "quit", "Quit")]

    # In Textual 7.x, MODES + switch_mode is the correct way to make a named
    # screen the active base screen. SCREENS + push_screen stacks on top of
    # _default, so app.query() searches _default (empty) instead of MainScreen.
    # MODES gives each entry its own screen stack; switch_mode makes it active
    # and app.query() then correctly searches MainScreen's widget tree.
    MODES: ClassVar[dict] = {
        'main':   MainScreen,
    }
    DEFAULT_MODE: ClassVar[str] = 'main'

    # These are still registered as named screens for push/pop overlays
    SCREENS: ClassVar[dict] = {
        'create': CreateScreen,
        'help':   HelpScreen,
        'quit':   QuitScreen,
        'load':   LoadingScreen,
    }

    def __init__(self, context: RunconfContext, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = RunconfUIBackend(context)

    def on_mount(self) -> None:
        self.theme = "catppuccin-latte"
        self.title = f"Runconf-Shifter-UI v{version('runconf_ui')}"
        self.switch_mode('main')
        self.call_after_refresh(self._init_file_selects)

    # ------------------------------------------------------------------ #
    # File select handlers                                                 #
    # ------------------------------------------------------------------ #

    @on(runconf_msg.DaqVersionSelectedMessage)
    def handle_version_selected(self, event: runconf_msg.DaqVersionSelectedMessage):
        self.backend.set_daq_version(event.daq_version)
        available_sessions = self.backend.get_sessions()
        for file_select in self.query(FileSelect):
            file_select.enable_session_select()
            file_select.update_sessions(available_sessions)

    @on(runconf_msg.DaqSessionSelectedMessage)
    def handle_session_selected(self, event: runconf_msg.DaqSessionSelectedMessage):
        self.backend.set_daq_session(event.daq_session)
        for file_select in self.query(FileSelect):
            file_select.enable_open_button()

    # ------------------------------------------------------------------ #
    # Config load handlers                                                 #
    # ------------------------------------------------------------------ #

    @on(runconf_msg.LoadConfigMessage)
    def handle_load_config(self, _: runconf_msg.LoadConfigMessage) -> None:
        try:
            self.push_screen('load')
        except Exception:
            import traceback
            self.notify(traceback.format_exc(), title="Screen Push Failed", severity="error", timeout=30)
            return
        self._load_config_worker()

    @work(thread=True)
    def _load_config_worker(self) -> None:
        self.backend.open_selected_session()
        self.app.call_from_thread(self._on_config_loaded)

    def _on_config_loaded(self) -> None:
        self.pop_screen()
        self._refresh_enabled_info(load_fresh=True)
        self.refresh()

    def _on_config_failed(self, error_msg: str) -> None:
        self.pop_screen()
        self.notify(error_msg, title="Config Load Failed", severity="error", timeout=30)

    # ------------------------------------------------------------------ #
    # Quit / create / help handlers                                        #
    # ------------------------------------------------------------------ #

    @on(runconf_msg.OpenQuitMenuMessage)
    def handle_open_quit(self):
        self.push_screen(QuitScreen(self.backend.configuration is not None))

    @on(runconf_msg.OpenCreateMenuMessage)
    def handle_open_create(self):
        self.push_screen('create')

    @on(runconf_msg.QuitAndSaveMessage)
    def handle_quit_save(self):
        self.backend.save_config()
        self.exit()

    @on(runconf_msg.QuitAndScrapMessage)
    def handle_quit_scrap(self):
        self.exit()

    @on(runconf_msg.CancelQuitMessage)
    def handle_cancel_quit(self):
        self.pop_screen()

    @on(runconf_msg.OpenHelpMenuMessage)
    def handle_help(self):
        self.push_screen('help')

    # ------------------------------------------------------------------ #
    # Node toggle handler                                                  #
    # ------------------------------------------------------------------ #

    @on(runconf_msg.NodeToggledMessage)
    def handle_node_toggled(self, event: runconf_msg.NodeToggledMessage):
        self.backend.toggle(event.group_id, event.widget_id)
        self._refresh_enabled_info(load_fresh=False)

    # ------------------------------------------------------------------ #
    # Shared UI refresh                                                    #
    # ------------------------------------------------------------------ #

    def _refresh_enabled_info(self, load_fresh: bool = False) -> None:
        dis_info    = self.backend.get_disableable_values()
        adj_info    = self.backend.get_adjustable_values()
        tree_views  = self.backend.get_tree_views()
        config_tree = self.backend.get_config_tree()

        pairs = [
            (self.query(EnableDisableTabs),       dis_info),
            (self.query(AdjustableAttributeTabs), adj_info),
            (self.query(RichTreeTabbed),          tree_views),
            (self.query(ConfigTreePanel),         config_tree),
        ]
        for widgets, data in pairs:
            for widget in widgets:
                widget.load(data) if load_fresh else widget.update(data)

        opts_panel = self.query(OptionsPanel)
        if opts_panel:
            if self.backend.configuration is None:
                opts_panel.first().disable_selected()
            else:
                opts_panel.first().enable_all()

        file_select = self.query(FileSelect)
        if file_select:
            file_select.first().update_text(self.backend.info_text)

    def _init_file_selects(self) -> None:
        versions = self.backend.get_daq_versions()
        for file_select in self.query(FileSelect):
            file_select.update_versions(versions)
            file_select.refresh()

    # ------------------------------------------------------------------ #

    def exit(self):
        rc_command = "run drunc"
        super().exit(result=f"To run drunc please launch {rc_command}")