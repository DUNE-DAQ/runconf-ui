from rich.tree import Tree
from textual.containers import ScrollableContainer
from textual.widgets import Static

from .dynamic_panel import DynamicTabbedContent, textual_safe_id


class RichTreePanel(ScrollableContainer):
    """Panel widget for displaying a Rich Tree visualization.

    This widget displays a Rich Tree object in a scrollable container,
    allowing interactive viewing of hierarchical tree structures.
    """

    def __init__(self, tree: Tree, *args, **kwargs):
        """Initialize RichTreePanel with a Rich Tree.

        :param tree: The Rich Tree object to display
        :param args: Variable positional arguments passed to parent ScrollableContainer
        :param kwargs: Variable keyword arguments passed to parent ScrollableContainer
        """
        super().__init__(*args, **kwargs)
        self._tree = tree

    def compose(self):
        """Compose the tree display widget.

        :returns: A generator yielding the static widget containing the tree
        """
        yield Static(self._tree, id="tree_view")

    def update_tree(self, tree: Tree):
        """Update the displayed tree.

        :param tree: The new Rich Tree to display
        """
        self._tree = tree
        view = self.query_one("#tree_view", Static)
        view.update(self._tree)


class RichTreeTabbed(DynamicTabbedContent):
    """Tabbed widget containing tree panels for multiple groups.

    Manages multiple RichTreePanel tabs, one for each group of hierarchical
    data to be displayed as a tree.
    """

    panel_prefix = "tree_panel"

    def _make_pane_content(
        self, group_id: str, data: Tree, panel_id: str
    ) -> RichTreePanel:
        """Create a RichTreePanel for the given tree.

        :param group_id: The identifier for this group
        :param data: The Rich Tree to display
        :param panel_id: The widget ID to assign to the panel
        :returns: A new RichTreePanel widget
        :rtype: RichTreePanel
        """
        return RichTreePanel(data, id=panel_id)

    def _update_panes(self, data: dict) -> None:
        """Update all tree panes with new tree data.

        :param data: Dictionary mapping group IDs to Rich Tree objects
        """
        for group_id, tree in data.items():
            group_id_safe = textual_safe_id(group_id)
            panel_id = self._panel_id(group_id_safe)
            results = self.query(f"#{panel_id}")
            if not results:
                continue
            panel = results.first(RichTreePanel)
            panel.update_tree(tree)


class ConfigTreePanel(ScrollableContainer):
    """Panel widget for displaying the full DAQ configuration tree.

    Displays the complete hierarchical configuration structure in a
    Rich Tree format within a scrollable container.
    """

    def __init__(self, *args, **kwargs):
        """Initialize ConfigTreePanel.

        :param args: Variable positional arguments passed to parent ScrollableContainer
        :param kwargs: Variable keyword arguments passed to parent ScrollableContainer
        """
        super().__init__(*args, **kwargs)
        self._tree = Tree("No Config Loaded")

    def compose(self):
        """Compose the configuration tree display widget.

        :returns: A generator yielding the static widget containing the tree
        """
        yield Static(self._tree, id="config_tree_view", classes="config_tree_view")

    def load(self, tree: Tree) -> None:
        """Load and display a new configuration tree.

        Performs a full rebuild to display the new tree structure.

        :param tree: The new Rich Tree to display
        """
        self._tree = tree
        self.refresh(recompose=True)

    def update(self, tree: Tree) -> None:
        """Update the displayed configuration tree without rebuilding.

        Efficiently updates the tree content without recreating the widget.

        :param tree: The updated Rich Tree to display
        """
        self._tree = tree
        self.query_one("#config_tree_view", Static).update(tree)
