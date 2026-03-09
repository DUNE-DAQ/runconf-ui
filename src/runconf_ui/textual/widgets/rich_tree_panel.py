from rich.tree import Tree
from textual.containers import ScrollableContainer
from textual.widgets import Static

from .dynamic_panel import DynamicTabbedContent, textual_safe_id


class RichTreePanel(ScrollableContainer):
    def __init__(self, tree: Tree, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tree = tree

    def compose(self):
        yield Static(self._tree, id="tree_view")

    def update_tree(self, tree: Tree):
        self._tree = tree
        view = self.query_one("#tree_view", Static)
        view.update(self._tree)


class RichTreeTabbed(DynamicTabbedContent):
    panel_prefix = "tree_panel"

    def _make_pane_content(self, group_id: str, data: Tree, panel_id: str) -> RichTreePanel:
        return RichTreePanel(data, id=panel_id)

    def _update_panes(self, data: dict) -> None:
        for group_id, tree in data.items():
            group_id_safe = textual_safe_id(group_id)
            panel_id      = self._panel_id(group_id_safe)
            results = self.query(f"#{panel_id}")
            if not results:
                continue
            panel = results.first(RichTreePanel)
            panel.update_tree(tree)
