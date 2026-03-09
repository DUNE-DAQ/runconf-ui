# runconf-ui

from textual import on
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, TabPane, TabbedContent

from ..widgets import (
    EnableDisableTabs,
    AdjustableAttributeTabs,
    RichTreeTabbed,
    FileSelect,
    OptionsPanel,
)


class MainScreen(ModalScreen):
    def compose(self):
        yield Header()
        with Grid(id="main_container"):
            yield FileSelect(id="file-select-panel")
            with Grid(id="enable_disable_panel_container"):
                with TabbedContent("Controls", id="selection_adjust_tabs"):
                    with TabPane("Enable/Disable"):
                        yield EnableDisableTabs(id="selection_tabs")
                    # with TabPane("Adjustable"):
                    #     yield AdjustableAttributeTabs(id="adjustable_tabs")

                with TabbedContent("Schematic Views", id="control_maps_tabs"):
                    with TabPane("System Maps"):
                        yield RichTreeTabbed(id="maps_panel")

                    with TabPane("Adjustable"):
                        yield AdjustableAttributeTabs(id="adjustable_tabs")


            yield OptionsPanel(id="option_panel_main")
        yield Footer()