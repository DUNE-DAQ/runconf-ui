import re

from textual import on
from textual.containers import ScrollableContainer
from textual.widgets import Button
from runconf_ui.state_tree import NodeStatus

from ..messages import NodeToggledMessage
from .dynamic_panel import DynamicTabbedContent, textual_safe_id


class EnableDisablePanel(ScrollableContainer):
    def __init__(self, group_id: str, nodes: dict[str, NodeStatus], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._group_id = group_id
        self._runconf_nodes = nodes

    def compose(self):
        for node_id, node in self._runconf_nodes.items():
            cls     = "node_enabled" if node.is_enabled else "node_disabled"
            enabled = node.is_interactive
            yield Button(
                label=node.node.label,
                id=node_id,
                classes=f"enable_disable_button {cls}",
                disabled=not enabled,
            )

    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed):
        self.post_message(NodeToggledMessage(group_id=self._group_id, widget_id=event.button.id))


    def update_buttons(self, nodes: dict[str, NodeStatus]) -> None:
        for node_id, node in nodes.items():
            results = self.query(f"#{node_id}")
            if not results:
                continue
            button = results.first(Button)
            button.remove_class("node_enabled", "node_disabled")
            button.add_class("node_enabled" if node.is_enabled else "node_disabled")
            button.disabled = not node.is_interactive


class EnableDisableTabs(DynamicTabbedContent):
    panel_prefix = "enable_disable_panel"

    def _make_pane_content(self, group_id: str, data: dict[str, NodeStatus], panel_id: str) -> EnableDisablePanel:
        return EnableDisablePanel(group_id, data, id=panel_id)

    def _update_panes(self, data: dict) -> None:
        for group_id, nodes in data.items():
            group_id_safe = textual_safe_id(group_id)
            panel_id      = self._panel_id(group_id_safe)
            results = self.query(f"#{panel_id}")
            if not results:
                continue
            panel = results.first(EnableDisablePanel)
            panel.update_buttons(nodes)
