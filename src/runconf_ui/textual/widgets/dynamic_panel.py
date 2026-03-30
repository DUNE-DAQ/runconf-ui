import re
from abc import abstractmethod

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import TabbedContent, TabPane

from runconf_ui.utils import get_logger

_TEXTUAL_UNSAFE = re.compile(r"[^-a-zA-Z0-9_:]")


def textual_safe_id(input_id: str) -> str:
    return _TEXTUAL_UNSAFE.sub("_", input_id)


class DynamicTabbedContent(Widget):
    """
    Wrapper widget that owns a TabbedContent and rebuilds it from scratch
    on load() by recomposing this outer container — not the TabbedContent
    itself, which is unsafe to recompose.
    """

    panel_prefix: str = "panel"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data = {}

    @abstractmethod
    def _make_pane_content(self, group_id: str, data, panel_id: str) -> Widget: ...

    @abstractmethod
    def _update_panes(self, data: dict) -> None:
        """Update existing pane contents in place."""
        ...

    def _panel_id(self, group_id_safe: str) -> str:
        return f"{self.panel_prefix}_{group_id_safe}"

    def compose(self) -> ComposeResult:
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
        """Full rebuild — only call when tabs themselves change (new config)."""
        get_logger().debug(f"Loading new data {data}")
        self._data = data

        self.refresh(recompose=True)

    def update(self, data: dict) -> None:
        """Update existing pane contents without rebuilding tabs."""
        self._data = data
        self._update_panes(data)
