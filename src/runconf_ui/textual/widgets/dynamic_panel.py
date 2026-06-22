import re
from abc import abstractmethod

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import TabbedContent, TabPane

from runconf_ui.utils import get_logger

_TEXTUAL_UNSAFE = re.compile(r"[^-a-zA-Z0-9_:]")


def textual_safe_id(input_id: str) -> str:
    """Convert an arbitrary string to a Textual-safe widget ID.

    Replaces non-alphanumeric characters (except hyphens, underscores, colons)
    with underscores to ensure the string is valid for use as a Textual widget ID.

    :param input_id: The input string to convert
    :returns: A Textual-safe version of the input string
    :rtype: str
    """
    return _TEXTUAL_UNSAFE.sub("_", input_id)


class DynamicTabbedContent(Widget):
    """Wrapper widget that owns a TabbedContent and rebuilds it dynamically.

    This widget manages a Textual TabbedContent and rebuilds it from scratch
    on load() by recomposing the outer container rather than the TabbedContent
    itself, which is unsafe to recompose directly.

    Subclasses must implement _make_pane_content() and _update_panes() to define
    how tab panes are created and updated.
    """

    panel_prefix: str = "panel"

    def __init__(self, *args, **kwargs):
        """Initialize DynamicTabbedContent.

        :param args: Variable positional arguments passed to parent Widget
        :param kwargs: Variable keyword arguments passed to parent Widget
        """
        super().__init__(*args, **kwargs)
        self._data = {}

    @abstractmethod
    def _make_pane_content(self, group_id: str, data, panel_id: str) -> Widget:
        """Create the widget content for a tab pane.

        Subclasses must implement this method to create the appropriate widget
        for displaying the content of a specific tab pane.

        :param group_id: The identifier for this tab group
        :param data: The data to populate the pane content
        :param panel_id: The widget ID to assign to the created panel
        :returns: A Widget containing the pane content
        :rtype: Widget
        """
        ...

    @abstractmethod
    def _update_panes(self, data: dict) -> None:
        """Update existing pane contents in place.

        Subclasses must implement this method to update the content of existing
        tab panes without recreating them, for efficiency.

        :param data: The new data to update panes with
        """
        ...

    def _panel_id(self, group_id_safe: str) -> str:
        """Generate a panel widget ID from a group identifier.

        :param group_id_safe: A Textual-safe group identifier
        :returns: The panel widget ID
        :rtype: str
        """
        return f"{self.panel_prefix}_{group_id_safe}"

    def compose(self) -> ComposeResult:
        """Compose the widget hierarchy for display.

        Creates a TabbedContent widget with tab panes for each group in the
        current data dictionary.

        :returns: A generator yielding composed child widgets
        :rtype: ComposeResult
        """
        get_logger().debug(f"Composing DynamicTabbedContent ({self.id})")
        with TabbedContent():
            for group_id, group_data in self._data.items():
                get_logger().debug(f"Adding {group_id}")

                group_id_safe = textual_safe_id(group_id)
                panel_id = self._panel_id(group_id_safe)
                get_logger().debug(f"   Adding panel {panel_id}")

                pane_id = f"{self.panel_prefix}_{group_id_safe}_pane"  # namespaced
                get_logger().debug(f"   Adding pane {pane_id}")
                panel = self._make_pane_content(group_id, group_data, panel_id)
                yield TabPane(group_id, panel, id=pane_id)

    def load(self, data: dict) -> None:
        """Load new data and rebuild all tabs.

        Performs a full rebuild of the tab structure. Only call when tabs
        themselves change (e.g., new configuration loaded). For updating
        existing pane contents, use update() instead.

        :param data: The new data dictionary mapping group IDs to group data
        """
        get_logger().debug(f"Loading new data {data}")
        self._data = data

        self.refresh(recompose=True)

    def update(self, data: dict) -> None:
        """Update existing pane contents without rebuilding tabs.

        Efficiently updates the content of existing tab panes without recreating
        the widget structure. Use this for updates to existing data rather than
        calling load() again.

        :param data: The updated data dictionary for existing groups
        """
        self._data = data
        self._update_panes(data)
