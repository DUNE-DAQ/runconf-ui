"""
Textual application for controlling runconf-shifter-ui.
"""

from importlib.metadata import version
from typing import Any, ClassVar

from textual import on, work
from textual.app import App
from textual.css.query import DOMQuery

from runconf_ui.backend import RunconfUIBackend
from runconf_ui.textual import messages as runconf_msg
from runconf_ui.textual.screens import (
    CreateScreen,
    ExceptionScreen,
    HelpScreen,
    MainScreen,
    QuitScreen,
)
from runconf_ui.textual.screens.popup_screens import LoadingScreen
from runconf_ui.textual.widgets import (
    AdjustableAttributeTabs,
    ConfigTreePanel,
    FileSelect,
    IncludeExcludeTabs,
    OptionsPanel,
    RichTreeTabbed,
)
from runconf_ui.utils import get_logger

# No neat way to type this sadly
NodeIterator = list[tuple[DOMQuery, Any]]


class RunconfUIApp(App):
    """Main Textual application for runconf-shifter-ui.

    Manages the TUI interface for selecting and configuring DAQ sessions,
    displaying configuration trees, and managing include/exclude and adjustable
    attributes through an interactive terminal interface.
    """

    CSS_PATH: ClassVar[str] = "runconf_shifter_ui.tcss"
    BINDINGS: ClassVar[list] = [("ctrl+q", "quit", "Quit")]

    #: Named screen modes for the application. Uses ``switch_mode`` to set the
    #: active base screen. Each entry gets its own screen stack so that
    #: ``app.query()`` correctly searches the active screen's widget tree.
    MODES: ClassVar[dict] = {
        "main": MainScreen,
    }
    DEFAULT_MODE: ClassVar[str] = "main"

    # These are still registered as named screens for push/pop overlays
    SCREENS: ClassVar[dict] = {
        "help": HelpScreen,
    }

    def __init__(self, backend: RunconfUIBackend, *args, **kwargs):
        """Initialize RunconfUIApp.

        :param backend: The RunconfUIBackend instance managing configuration logic
        :param args: Positional arguments passed to App
        :param kwargs: Keyword arguments passed to App
        """
        super().__init__(*args, **kwargs)
        self.backend = backend
        # Backends shared with other frontends (RpcBackend) report every change
        # to the shared state; the in-process backend does not.
        self._shared = callable(getattr(backend, "add_listener", None))
        self._shown_revision = -1  # shared-state revision the panels show
        self._loaded_snapshot: int | None = None  # snapshot the panels were built from
        self._quitting = False
        get_logger().debug("Initialised application")

    def on_mount(self) -> None:
        """Initialize the application on Textual mount event.

        Sets theme, title, and initializes file selectors.
        """
        get_logger().debug("Mounting")
        self.theme = "catppuccin-latte"
        self.title = f"Runconf-Shifter-UI v{version('runconf_ui')}"
        self.switch_mode("main")
        self.push_screen(LoadingScreen("Initialising..."))
        self.call_after_refresh(self._init_file_selects)
        if self._shared:
            # Called on the backend's stream thread; post_message is thread-safe
            self.backend.add_listener(
                lambda change: self.post_message(
                    runconf_msg.SharedStateChangedMessage(change)
                )
            )
        get_logger().debug("Mounted")

    # ------------------------------------------------------------------ #
    # File select handlers                                                 #
    # ------------------------------------------------------------------ #

    @on(runconf_msg.DaqVersionSelectedMessage)
    def handle_version_selected(self, event: runconf_msg.DaqVersionSelectedMessage):
        get_logger().info(f"Selected daq version: {event.daq_version}")
        self.push_screen(LoadingScreen("Scanning for available sessions..."))  # ← first
        self._fetch_sessions_worker(event.daq_version)

    @work(thread=True)
    def _fetch_sessions_worker(self, daq_version) -> None:
        try:
            self.backend.set_daq_version(daq_version)  # ← moved into worker
            sessions = self.backend.get_sessions()
            get_logger().debug(f"Available Sessions: {sessions}")
            self.app.call_from_thread(self._apply_sessions, sessions)
        except Exception as e:
            get_logger().exception(e)
            self.app.call_from_thread(self._on_config_failed_popup, e)

    def _apply_sessions(self, sessions) -> None:
        """Populate session selects and dismiss the loading screen.

        :param sessions: List of available DAQ sessions
        """
        for file_select in self.query(FileSelect):
            file_select.enable_session_select()
            file_select.update_sessions(sessions)
        if isinstance(self.screen, LoadingScreen):
            self.pop_screen()

    @on(runconf_msg.DaqSessionSelectedMessage)
    def handle_session_selected(self, event: runconf_msg.DaqSessionSelectedMessage):
        self.backend.set_daq_session(event.daq_session)
        get_logger().info(f"Selected daq session: {event.daq_session}")
        for file_select in self.query(FileSelect):
            file_select.enable_open_button()

    # ------------------------------------------------------------------ #
    # Config load handlers                                                 #
    # ------------------------------------------------------------------ #

    @on(runconf_msg.LoadConfigMessage)
    def handle_load_config(self, _: runconf_msg.LoadConfigMessage) -> None:
        get_logger().debug("Pushing config load")
        if isinstance(self.screen, LoadingScreen):
            self.pop_screen()

        self.push_screen(LoadingScreen("Opening Configuration..."))
        self._load_config_worker()

    @work(thread=True)
    def _load_config_worker(self) -> None:
        try:
            self.backend.open_selected_session()
            self.app.call_from_thread(self._on_config_loaded)
        except Exception as e:
            self.app.call_from_thread(self._on_config_failed_popup, e)

    def _on_config_loaded(self) -> None:
        self.pop_screen()
        self._refresh_included_info(load_fresh=True)
        self.refresh()

    def _on_config_failed_popup(self, e: Exception) -> None:
        self.pop_screen()  # dismiss the loading screen first
        self.handle_exception_popup(e)

    # ------------------------------------------------------------------ #
    # Quit / create / help handlers                                        #
    # ------------------------------------------------------------------ #

    @on(runconf_msg.OpenQuitMenuMessage)
    def handle_open_quit(self):
        self.push_screen(QuitScreen(self.backend.configuration is not None))

    @on(runconf_msg.OpenCreateMenuMessage)
    def handle_open_create(self):
        self.push_screen(CreateScreen())

    @on(runconf_msg.QuitAndSaveMessage)
    def handle_quit_save(self):
        self._quitting = True
        try:
            self.backend.save_config()
        except Exception as e:
            self.handle_exception_popup(e)
        self.exit()

    @on(runconf_msg.QuitAndScrapMessage)
    def handle_quit_scrap(self):
        self._quitting = True
        self.exit()

    @on(runconf_msg.CancelQuitMessage)
    def handle_cancel_quit(self):
        self.pop_screen()

    @on(runconf_msg.OpenHelpMenuMessage)
    def handle_help(self):
        self.push_screen("help")

    def handle_exception_popup(self, exception: Exception) -> None:
        get_logger().error(f"Error during operation: {exception}")
        self.push_screen(ExceptionScreen(str(exception)))

    # ------------------------------------------------------------------ #
    # Node toggle handler                                                  #
    # ------------------------------------------------------------------ #

    @on(runconf_msg.NodeToggledMessage)
    def handle_node_toggled(self, event: runconf_msg.NodeToggledMessage):
        get_logger().info(f"Toggled {event.group_id} : {event.widget_id}")

        self.backend.toggle(event.group_id, event.widget_id)
        self._refresh_included_info(load_fresh=False)

    @on(runconf_msg.ValueChangedMessage)
    def handle_value_changed(self, event: runconf_msg.ValueChangedMessage):
        get_logger().info(
            f"Value changed for {event.group_id} : {event.widget_id} -> {event.new_value}"
        )

        self.backend.set_value(event.group_id, event.widget_id, event.new_value)
        self._refresh_included_info(load_fresh=False)

    # ------------------------------------------------------------------ #
    # Changes from other frontends sharing the server                      #
    # ------------------------------------------------------------------ #

    @on(runconf_msg.SharedStateChangedMessage)
    def handle_shared_state_changed(
        self, event: runconf_msg.SharedStateChangedMessage
    ) -> None:
        change = event.change
        get_logger().debug(f"Shared state changed: {change}")
        if change.kind == "shutdown":
            if self._quitting:
                return  # our own quit; already exiting
            self.exit(message=f"The runconf-ui server shut down: {change.message}")
            return
        if change.kind == "disconnected":
            self.handle_exception_popup(
                RuntimeError(f"Lost the connection to the server: {change.message}")
            )
            return
        if change.kind == "snapshot":
            self._sync_file_selects()
        # Our own changes were drawn when they returned; skip what is shown already
        if change.revision > self._shown_revision and (
            self.backend.configuration is not None
        ):
            self._refresh_included_info(load_fresh=False)

    def _sync_file_selects(self) -> None:
        """Show the server's dropdown selection (made by any frontend)."""
        for file_select in self._main_screen().query(FileSelect):
            file_select.show_selection(
                self.backend.get_daq_versions(),
                self.backend.get_current_version(),
                self.backend.get_sessions(),
                self.backend.get_current_session(),
            )

    def _main_screen(self):
        """The base screen holding the panels, even while a popup is on top."""
        return self.screen_stack[0] if self.screen_stack else self.screen

    # ------------------------------------------------------------------ #
    # Shared UI refresh                                                    #
    # ------------------------------------------------------------------ #

    def _refresh_included_info(self, load_fresh: bool = False) -> None:

        get_logger().debug("Refreshing included info")

        if self._shared:
            # Read the revision first: the cache only moves forward from here
            self._shown_revision = self.backend.revision
            snapshot = self.backend.snapshot_revision
            # A new snapshot (open/reset) may bring different nodes: rebuild panels
            load_fresh = load_fresh or snapshot != self._loaded_snapshot
            self._loaded_snapshot = snapshot

        dis_info = self.backend.get_excludable_values()
        adj_info = self.backend.get_adjustable_values()
        tree_views = self.backend.get_tree_views()
        config_tree = self.backend.get_config_tree()

        screen = self._main_screen()
        pairs: NodeIterator = [
            (screen.query(IncludeExcludeTabs), dis_info),
            (screen.query(AdjustableAttributeTabs), adj_info),
            (screen.query(RichTreeTabbed), tree_views),
            (screen.query(ConfigTreePanel), config_tree),
        ]
        for widgets, data in pairs:
            if not widgets:
                continue

            for widget in widgets:
                widget.load(data) if load_fresh else widget.update(data)
                get_logger().debug("Loading %s to %s", data, widget.id)

        opts_panel = screen.query(OptionsPanel)
        if opts_panel:
            get_logger().debug("Loading options")
            if self.backend.configuration is None:
                opts_panel.first().disable_selected()
                get_logger().debug("Disabling Opts")
            else:
                opts_panel.first().enable_all()
                get_logger().debug("Enabling Opts")

        file_select = screen.query(FileSelect)
        if file_select:
            file_select.first().update_text(self.backend.info_text)

        self.refresh()

    def _init_file_selects(self) -> None:
        if self._shared and self.backend.get_current_version() is not None:
            # Joining a server another frontend already set up: show its state
            # rather than picking defaults, which would reset its selection
            self._join_shared_state()
            return
        try:
            versions = self.backend.get_daq_versions()
            get_logger().debug(f"Initialising file selects with {versions}")
            for file_select in self.query(FileSelect):
                file_select.update_versions(versions)
                file_select.set_default_version(self.backend.get_default_version())
                file_select.refresh()
                if isinstance(self.screen, LoadingScreen):
                    self.pop_screen()
        except Exception as e:
            get_logger().exception(e)
            if isinstance(self.screen, LoadingScreen):
                self.pop_screen()
            self.handle_exception_popup(e)

    def _join_shared_state(self) -> None:
        if isinstance(self.screen, LoadingScreen):
            self.pop_screen()
        try:
            self._sync_file_selects()
            if self.backend.configuration is not None:
                self._refresh_included_info(load_fresh=True)
        except Exception as e:
            get_logger().exception(e)
            self.handle_exception_popup(e)
