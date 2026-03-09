# runconf-ui

from textual import on
from textual.containers import Grid, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Label

from ..widgets import (
    EnableDisableTabs,
    FileSelect,
    OptionsPanel,
    RichTreeTabbed,
)


class MainScreen(ModalScreen):
    def compose(self):
        with ScrollableContainer(id="main-screen-container"):
            with ScrollableContainer(id="file-select-container"):
                yield FileSelect(id="file-select-panel")

            with Grid(id="main-content-grid"):
                yield EnableDisableTabs(id="enable-disable-tabs")
                yield RichTreeTabbed(id="rich-tree-tabbed")

            yield OptionsPanel(id="options-panel")

        yield Header()
        yield Footer()