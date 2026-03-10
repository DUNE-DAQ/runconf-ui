'''
Textual application for controlling runconf-shifter-ui
'''
from typing import ClassVar

from textual import on, work
from textual.app import App

from runconf_ui.backend import RunconfContext, RunconfUI
from runconf_ui.textual import messages as runconf_msg
from runconf_ui.textual.screens import (CreateScreen,
                                        MainScreen,
                                        QuitScreen,
                                        HelpScreen)
from runconf_ui.textual.screens.popup_screens import LoadingScreen
from runconf_ui.textual.widgets import (
    AdjustableAttributeTabs,
    EnableDisableTabs,
    FileSelect,
    RichTreeTabbed,
    OptionsPanel,
    ConfigTreePanel
)


class RunconfUIApp(App):

    CSS_PATH: ClassVar[str] = "runconf_shifter_ui.tcss"
    BINDINGS: ClassVar[list[tuple]] = [("ctrl+q", "quit", "Quit")]
    SCREENS: ClassVar[dict] = {
        'main': MainScreen,
        'create': CreateScreen,
        'quit': QuitScreen,
        'load': LoadingScreen,
        'help': HelpScreen
    }

    def __init__(self, context: RunconfContext, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = RunconfUI(context)

    def on_mount(self) -> None:
        self.theme = "catppuccin-latte"
        self.push_screen('main')
        self.call_after_refresh(self._init_file_selects)

    def _refresh_enabled_info(self, load_fresh: bool = False):
        dis_info   = self.backend.get_disableable_values()
        adj_info   = self.backend.get_adjustable_values()
        tree_views = self.backend.get_tree_views()
        config_tree = self.backend.get_config_tree()

        pairs = [
            (self.query(EnableDisableTabs),       dis_info),
            (self.query(AdjustableAttributeTabs), adj_info),
            (self.query(RichTreeTabbed),          tree_views),
            (self.query(ConfigTreePanel),         config_tree)
        ]
        for widgets, data in pairs:
            for widget in widgets:
                widget.load(data) if load_fresh else widget.update(data)

        # Now
        opts_panel = self.query(OptionsPanel)
        if not opts_panel:
            return
        
        if self.backend.configuration is None:
            opts_panel.first().disable_selected()
        else:
            opts_panel.first().enable_all()

        # Now update the file_panel
        file_select = self.query(FileSelect)
        if file_select:        
            file_select.first().update_text(
                self.backend.info_text
            )


    def _init_file_selects(self) -> None:
        versions = self.backend.get_daq_versions()
        for file_select in self.query(FileSelect):
            file_select.update_versions(versions)
            file_select.refresh()

    # ------------------------------------------------------------------ #
    # Message handling
    # ------------------------------------------------------------------ #
    @on(runconf_msg.NodeToggledMessage)
    def handle_node_toggled(self, event: runconf_msg.NodeToggledMessage):
        self.backend.toggle(event.group_id, event.widget_id)
        self._refresh_enabled_info(False)

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
    # Quit Screen Message Handling
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
        self.app.exit()

    @on(runconf_msg.QuitAndScrapMessage)
    def handle_quit_scrap(self):
        self.app.exit()
    
    @on(runconf_msg.CancelQuitMessage)
    def handle_cancel_quit(self):
        self.pop_screen()
    
    @on(runconf_msg.OpenHelpMenuMessage)
    def handle_help(self):
        self.push_screen('help')
    
    # ------------------------------------------------------------------ #
    # Config loading
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
        self._refresh_enabled_info(True)
        self.refresh()
        
    def _on_config_failed(self, error_msg: str) -> None:
        self.pop_screen()
        self.notify(error_msg, title="Config Load Failed", severity="error", timeout=30)

if __name__ == "__main__":
    import os
    import shutil
    from pathlib import Path

    from daqconf.consolidate import consolidate_db

    test_conf = Path(
        os.environ.get("DAQSYSTEMTEST_SHARE", "")
        + "/config/daqsystemtest/example-configs.data.xml"
    )

    tmp_path = Path("/tmp/runconf-test")
    tmp_path.mkdir(parents=True, exist_ok=True)
    dummy_conf = str(tmp_path / "dummy.data.xml")

    consolidate_db(str(test_conf), str(dummy_conf), "local-1x1-config")

    runconf_dir = tmp_path / "runconf-ui-settings"
    runconf_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy(
        Path("/home/hwallace/scratch/dune_software/daq/daq_work_areas/NFD_DEV_260205_A9/pythoncode/runconf-ui-refactor/tests/test_files/dummy.yml"),
        runconf_dir / "dummy.yml",
    )

    context = RunconfContext(apparatus="dummy", conf_directory=tmp_path, use_local=True)
    app = RunconfUIApp(context=context)
    app.run()