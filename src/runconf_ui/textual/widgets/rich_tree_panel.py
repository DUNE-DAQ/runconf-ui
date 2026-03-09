from rich.tree import Tree
from textual.containers import ScrollableContainer
from textual.widgets import Static

from .dynamic_panel import DynamicTabbedContent


class RichTreePanel(ScrollableContainer):
    def __init__(self, tree: Tree, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tree = tree

    def compose(self):
        yield Static(self._tree, id="tree_view")


class RichTreeTabbed(DynamicTabbedContent):
    panel_prefix = "tree_panel"

    def _make_pane_content(self, group_id: str, data: Tree, panel_id: str) -> RichTreePanel:
        return RichTreePanel(data, id=panel_id)
