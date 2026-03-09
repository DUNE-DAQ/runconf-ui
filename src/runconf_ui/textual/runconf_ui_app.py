'''
Textual application for controlling runconf-shifter-ui
'''

from typing import ClassVar

from textual import on
from textual.app import App

from runconf_ui.backend import RunconfContext, RunconfUI
from runconf_ui.textual import messages as runconf_msg
from runconf_ui.textual.screens import MainScreen
from runconf_ui.textual.widgets import EnableDisableTabs, RichTreeTabbed, FileSelect


class RunconfUIApp(App):
    '''
    Main textual application for runconf-ui
    '''

    CSS_PATH = "runconf_shifter_ui.tcss"
    BINDINGS: ClassVar = [("ctrl+q", "quit", "Quit")]
    SCREENS = {"main": MainScreen}

    def __init__(self, context: RunconfContext, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = RunconfUI(context)

    def on_mount(self) -> None:
        self.push_screen("main")
        self.call_after_refresh(self._init_file_selects)

    def refresh_enabled_info(self):
        '''Reload all panels from current backend state.'''
        dis_info   = self.backend.get_disableable_values()
        tree_views = self.backend.get_tree_views()

        for panel in self.query(EnableDisableTabs):
            panel.load(dis_info)

        for tree in self.query(RichTreeTabbed):
            tree.load(tree_views)

    def _init_file_selects(self) -> None:
        versions = self.backend.get_daq_versions()
        for file_select in self.query(FileSelect):
            file_select.update_versions(versions)
            file_select.refresh()

    # ------------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------------
    @on(runconf_msg.NodeToggledMessage)
    def handle_node_toggled(self, event: runconf_msg.NodeToggledMessage):
        self.backend.toggle(event.group_id, event.widget_id)
        self.refresh_enabled_info()

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

    @on(runconf_msg.LoadConfigMessage)
    def handle_load_config(self, event: runconf_msg.LoadConfigMessage) -> None:
        self.backend.open_selected_session()
        self.refresh_enabled_info()
        self.refresh()


if __name__ == "__main__":
    from pathlib import Path
    import os
    import shutil
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