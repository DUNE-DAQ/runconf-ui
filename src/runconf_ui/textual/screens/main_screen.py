# runconf-ui

from textual import on
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Footer, Header

from ..widgets import (
    EnableDisableTabs,
    FileSelect,
    OptionsPanel,
    RichTreeTabbed,
)


class MainScreen(ModalScreen):
    def compose(self):
        yield Header()
        with Grid(id="main_container"):
            yield FileSelect(id="file-select-panel")
            with Grid(id="enable_disable_panel_container"):
                yield EnableDisableTabs(id="selection_tabs")
                yield RichTreeTabbed(id="buttons_panel")
            yield OptionsPanel(id="option_panel_main")
        yield Footer()