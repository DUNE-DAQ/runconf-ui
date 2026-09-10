from textual import on
from textual.containers import ScrollableContainer, Vertical
from textual.widgets import Button, Static

from runconf_ui.state_tree import NodeStatus
from runconf_ui.utils import get_logger

from ..messages import NodeToggledMessage
from .dynamic_panel import DynamicTabbedContent, textual_safe_id


class IncludeExcludeButtonScroller(ScrollableContainer):
    """Inner scrollable area containing the button groups for an IncludeExcludePanel."""

class IncludeExcludePanel(Vertical):
    """Panel widget displaying include/exclude toggle buttons for configuration nodes.

    This widget displays a label above a scrollable container of buttons
    representing nodes that can be included or excluded. Button appearance
    reflects the current included/excluded state, and interactivity is managed
    based on node status.
    """

    def __init__(self, group_id: str, nodes: dict[str, NodeStatus], *args, **kwargs):
        """Initialize IncludeExcludePanel.

        :param group_id: The identifier for this panel's node group
        :param nodes: Dictionary mapping node IDs to their current NodeStatus
        :param args: Variable positional arguments passed to parent Vertical
        :param kwargs: Variable keyword arguments passed to parent Vertical
        """
        super().__init__(*args, **kwargs)
        get_logger().info(f"Initialising include/exclude panel with id {group_id}")
        get_logger().debug(f"Initialising include/exclude panel with nodes {nodes}")

        self._group_id = group_id
        self.border_title = group_id
        self._runconf_nodes = nodes

    def compose(self):
        """Compose the label and scrollable button groups for this panel.

        :returns: A generator yielding the label Static and the scroller widget
        """
        # We're gonna structure things into a dict
        button_groups = {}

        get_logger().debug("Composing include/exclude panel")

        main_node_label = "main_include_btn"
        sub_node_label = "sub_include_btn"

        for node_id, node in self._runconf_nodes.items():
            get_logger().debug(f"   - {node_id} : {node}")

            included_state = "node_included" if node.is_included else "node_excluded"
            is_top = node.parent is None

            node_classes = (
                f"{main_node_label if is_top else sub_node_label} {included_state}"
            )

            btn = Button(
                label=node.node.label,
                id=node_id,
                classes=node_classes,
                disabled=not node.is_interactive,
            )
            if node.tooltip:
                btn.tooltip = node.tooltip

            group_box = node.parent.label if node.parent else node.label
            if group_box not in button_groups:
                button_groups[group_box] = []
            button_groups[group_box].append((is_top, btn))

        # Label sits above the scroll area so it's always visible
        yield Static(self._group_id, classes="en_group_txt")

        button_group_widgets = []
        for group_lab, btns in button_groups.items():
            btns_sorted = [btn for _, btn in sorted(btns, key=lambda x: not x[0])]

            if "main_include_btn" not in btns_sorted[0].classes:
                for b in btns_sorted:
                    b_cls = list(b.classes)
                    b_cls.pop(b_cls.index("sub_include_btn"))
                    b_cls.append("main_include_btn")
                    b.classes = b_cls

            vtcl = Vertical(*btns_sorted, classes="en_button_container")
            vtcl.border_title = group_lab
            button_group_widgets.append(vtcl)

        yield IncludeExcludeButtonScroller(*button_group_widgets)

    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed):
        """Handle button press events and emit NodeToggledMessage.

        When a button is pressed, emits a NodeToggledMessage to notify
        the backend of the state change.

        :param event: The Button.Pressed event
        """
        if event.button.id is None:
            return

        self.post_message(
            NodeToggledMessage(group_id=self._group_id, widget_id=event.button.id)
        )

    def update_buttons(self, nodes: dict[str, NodeStatus]) -> None:
        """Update button states to reflect current node status.

        Updates CSS classes, disabled state, and tooltips based on the
        current node status. Called when state tree changes.

        :param nodes: Dictionary mapping node IDs to their current NodeStatus
        """
        get_logger().debug("Updating buttons")

        for node_id, node in nodes.items():
            results = self.query(f"#{node_id}")
            if not results:
                get_logger().debug(f"Node : {node_id} not found")
                continue
            get_logger().debug(f"Node : {node_id} found")
            button = results.first(Button)
            button.remove_class("node_included", "node_excluded")
            button.add_class("node_included" if node.is_included else "node_excluded")
            get_logger().debug(f"   - State : {button.classes}")
            button.disabled = not node.is_interactive
            get_logger().debug(f"   - Button Enabled : {button.disabled}")
            button.tooltip = node.tooltip or None
            get_logger().debug(f"   - Tooltip : {button.tooltip}")


class IncludeExcludeTabs(DynamicTabbedContent):
    """Tabbed widget containing include/exclude panels for multiple node groups.

    This widget manages multiple IncludeExcludePanee tabs, one for each group
    of include/exclude nodes in the configuration.
    """

    panel_prefix = "include_exclude_panel"

    def _make_pane_content(
        self, group_id: str, data: dict[str, NodeStatus], panel_id: str
    ) -> IncludeExcludePanel:
        """Create an IncludeExcludePanel for the given group.

        :param group_id: The identifier for this group
        :param data: Dictionary of nodes in this group
        :param panel_id: The widget ID to assign to the panel
        :returns: A new IncludeExclude widget
        :rtype: IncludeExcludePanel
        """
        return IncludeExcludePanel(group_id, data, id=panel_id)

    def _update_panes(self, data: dict) -> None:
        """Update all include/exclude panes with new node status data.

        :param data: Dictionary mapping group IDs to node dictionaries
        """
        get_logger().debug(f"Updating pans for {self.id}")
        for group_id, nodes in data.items():
            get_logger().debug(f"{group_id}:")
            group_id_safe = textual_safe_id(group_id)
            get_logger().debug(f"    - Safe ID: {group_id_safe}")
            panel_id = self._panel_id(group_id_safe)
            get_logger().debug(f"    - Panel ID: {panel_id}")
            results = self.query(f"#{panel_id}")
            if not results:
                get_logger().debug("    Couldn't find panel, continuing")
                continue
            panel = results.first(IncludeExcludePanel)
            get_logger().debug("    Found panel")
            panel.update_buttons(nodes)
            get_logger().debug("    Panel updated")
