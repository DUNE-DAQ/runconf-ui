
from textual import on
from textual.containers import ScrollableContainer
from textual.widgets import Button

from runconf_ui.state_tree import NodeStatus
from runconf_ui.utils import get_logger

from ..messages import NodeToggledMessage
from .dynamic_panel import DynamicTabbedContent, textual_safe_id


class EnableDisablePanel(ScrollableContainer):
    def __init__(self, group_id: str, nodes: dict[str, NodeStatus], *args, **kwargs):
        super().__init__(*args, **kwargs)
        get_logger().info(f"Initialising enable/disable panel with id {group_id}")
        get_logger().debug(f"Initialising enable/disable panel with nodes {nodes}")
        
        self._group_id = group_id
        self._runconf_nodes = nodes

    def compose(self):
        get_logger().debug(f"Composing enable/disable panel")
        for node_id, node in self._runconf_nodes.items():
            get_logger().debug(f"   - {node_id} : {node}")

                        
            cls     = "node_enabled" if node.is_enabled else "node_disabled"
            enabled = node.is_interactive
            btn = Button(
                label=node.node.label,
                id=node_id,
                classes=f"enable_disable_button {cls}",
                disabled=not enabled,
            )
            if node.tooltip:
                btn.tooltip = node.tooltip
            yield btn

    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed):
        self.post_message(NodeToggledMessage(group_id=self._group_id, widget_id=event.button.id))

    def update_buttons(self, nodes: dict[str, NodeStatus]) -> None:
        get_logger().debug(f"Updating buttons")

        get_logger().debug(f"Updating buttons")
        for node_id, node in nodes.items():
            results = self.query(f"#{node_id}")
            if not results:
                get_logger().debug(f"Node : {node_id} not found")
                continue
            get_logger().debug(f"Node : {node_id} found")
            button = results.first(Button)
            button.remove_class("node_enabled", "node_disabled")
            button.add_class("node_enabled" if node.is_enabled else "node_disabled")
            get_logger().debug(f"   - State : {button.classes}")
            button.disabled = not node.is_interactive
            get_logger().debug(f"   - Enabled : {button.disabled}")
            button.tooltip = node.tooltip or None
            get_logger().debug(f"   - Tooltip : {button.tooltip}")


class EnableDisableTabs(DynamicTabbedContent):
    panel_prefix = "enable_disable_panel"

    def _make_pane_content(self, group_id: str, data: dict[str, NodeStatus], panel_id: str) -> EnableDisablePanel:
        return EnableDisablePanel(group_id, data, id=panel_id)

    def _update_panes(self, data: dict) -> None:
        get_logger().debug(f"Updating pans for {self.id}")
        for group_id, nodes in data.items():
            get_logger().debug(f"{group_id}:")
            group_id_safe = textual_safe_id(group_id)
            get_logger().debug(f"    - Safe ID: {group_id_safe}")
            panel_id      = self._panel_id(group_id_safe)
            get_logger().debug(f"    - Panel ID: {panel_id}")
            results = self.query(f"#{panel_id}")
            if not results:
                get_logger().debug(f"    Couldn't find panel, continuing")
                continue
            panel = results.first(EnableDisablePanel)
            get_logger().debug(f"    Found panel")
            panel.update_buttons(nodes)
            get_logger().debug(f"    Panel updated")
