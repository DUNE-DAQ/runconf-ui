"""
Main screen for runconf-shifter-ui.
"""

from textual.containers import Grid
from textual.screen import Screen  # NOT ModalScreen
from textual.widgets import Footer, Header, TabbedContent, TabPane

from ..widgets import (
    AdjustableAttributeTabs,
    ConfigTreePanel,
    EnableDisableTabs,
    FileSelect,
    OptionsPanel,
    RichTreeTabbed,
)


class MainScreen(Screen):
    """Primary user interface screen for runconf-ui configuration management.

    Displays the main layout with file selection, control panels for enable/disable
    and adjustable attributes, configuration tree views, and application options.
    Provides the central interface for users to browse, select, and modify
    DAQ configurations.
    """

    def compose(self):
        """Compose the main screen layout hierarchy.

        Creates the header, main content grid with file selector, tabbed controls,
        tree views, and options panel, plus the footer.

        :returns: A generator yielding screen content widgets
        """
        yield Header()
        with Grid(id="main_container"):
            yield FileSelect(id="file-select-panel")
            with Grid(id="tabbed_content_container"):
                with TabbedContent(
                    "Controls", id="selection_adjust_tabs", classes="content_switcher"
                ):
                    with TabPane("Enable/Disable", classes="top_level_tab_pane"):
                        yield EnableDisableTabs(id="selection_tabs")

                with TabbedContent(
                    "Schematic Views",
                    id="control_maps_tabs",
                    classes="content_switcher",
                ):
                    with TabPane("Configuration", classes="top_level_tab_pane"):
                        yield ConfigTreePanel(id="config_tree_panel")

                    with TabPane("System Maps", classes="top_level_tab_pane"):
                        yield RichTreeTabbed(id="maps_panel")

                    with TabPane("Adjustable", classes="top_level_tab_pane"):
                        yield AdjustableAttributeTabs(id="adjustable_tabs")

            yield OptionsPanel(id="option_panel_main")
        yield Footer()
