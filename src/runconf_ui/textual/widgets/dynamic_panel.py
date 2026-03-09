import re
from abc import abstractmethod

from textual.widget import Widget
from textual.widgets import TabbedContent, TabPane

_TEXTUAL_UNSAFE = re.compile(r"[^-a-zA-Z0-9_]")


def textual_safe_id(input_id: str) -> str:
    '''Replaces unsafe characters in a Textual CSS ID with underscores.'''
    return _TEXTUAL_UNSAFE.sub("_", input_id)


class DynamicTabbedContent(TabbedContent):
    '''
    Base class for TabbedContent widgets populated via compose().
    Call load(data) to update data and recompose.
    '''

    panel_prefix: str = "panel"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data: dict = {}

    @abstractmethod
    def _make_pane_content(self, group_id: str, data, panel_id: str) -> Widget:
        '''Create the inner widget for a tab. Must pass panel_id to Widget.__init__.'''
        ...

    def _panel_id(self, group_id_safe: str) -> str:
        return f"{self.panel_prefix}_{group_id_safe}"

    def compose(self):
        for group_id, group_data in self._data.items():
            group_id_safe = textual_safe_id(group_id)
            panel_id      = self._panel_id(group_id_safe)
            # ID must be passed at construction time, not set afterwards
            panel = self._make_pane_content(group_id, group_data, panel_id)
            yield TabPane(group_id, panel, id=group_id_safe)

    def load(self, data: dict) -> None:
        '''Store new data and recompose.'''
        self._data = data
        self.refresh(recompose=True)