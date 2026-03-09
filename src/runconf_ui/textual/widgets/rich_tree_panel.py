import re

from rich.tree import Tree
from textual.containers import ScrollableContainer
from textual.widgets import Static

from .dynamic_panel import DynamicTabbedContent

# ---------------------------------------------------------------------------
# Rich Tree
# ---------------------------------------------------------------------------

class RichTreePanel(ScrollableContainer):
    '''Container for a single rich Tree view.'''

    def __init__(self, tree: Tree, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_tree = tree

    def compose(self):
        yield Static(self._initial_tree, id="tree_view")

    def update_tree(self, tree: Tree):
        self.query_one("#tree_view", Static).update(tree)


class RichTreeTabbed(DynamicTabbedContent):
    '''TabbedContent with one RichTreePanel per group that has a view_panel.'''

    panel_prefix = "tree_panel"

    def _make_pane_content(self, group_id: str, data: Tree) -> RichTreePanel:
        return RichTreePanel(data)

    def _update_pane(self, panel: RichTreePanel, data: Tree) -> None:
        panel.update_tree(data)