import re
from abc import abstractmethod

from textual.css.query import NoMatches
from textual.widget import Widget
from textual.widgets import TabbedContent, TabPane

_TEXTUAL_UNSAFE = re.compile(r"[^-a-zA-Z0-9_]")


def textual_safe_id(input_id: str) -> str:
    '''Replaces unsafe characters in a Textual CSS ID with underscores.'''
    return _TEXTUAL_UNSAFE.sub("_", input_id)


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------

class DynamicTabbedContent(TabbedContent):
    '''
    Base class for TabbedContent widgets populated dynamically.

    Subclasses implement:
      panel_prefix       — prefix for inner panel IDs
      _make_pane_content — produce the inner Widget for a tab

    Call load(data) to (re)build all tabs from scratch.
    '''

    panel_prefix: str = "panel"

    @abstractmethod
    def _make_pane_content(self, group_id: str, data) -> Widget:
        '''Create the inner widget for a new tab.'''
        ...

    def _panel_id(self, group_id_safe: str) -> str:
        return f"{self.panel_prefix}_{group_id_safe}"

    def load(self, data: dict):
        '''Remove all existing TabPanes and remount from fresh data.'''
        async def _remount():
            for pane in self.query(TabPane):
                await pane.remove()
            for group_id, group_data in data.items():
                group_id_safe = textual_safe_id(group_id)
                panel         = self._make_pane_content(group_id, group_data)
                panel.id      = self._panel_id(group_id_safe)
                await self.mount(TabPane(group_id, panel, id=group_id_safe))

        self.call_after_refresh(_remount)