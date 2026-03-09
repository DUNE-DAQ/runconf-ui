import re

from textual import on
from textual.containers import ScrollableContainer
from textual.widgets import Button
from textual.css.query import NoMatches

from runconf_ui.state_tree import NodeStatus

from ..messages import NodeToggledMessage
from .dynamic_panel import DynamicTabbedContent


class EnableDisablePanel(ScrollableContainer):
    '''
    Scrollable container holding one Button per disableable node.
    '''
    def __init__(self, runconf_nodes: dict[str, NodeStatus], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._runconf_nodes = runconf_nodes

    def compose(self):
        for node_id, node in self._runconf_nodes.items():
            # Skip nodes with IDs that start with __ (anonymous parent path)
            if node_id.startswith("_"):
                continue
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
        self.post_message(NodeToggledMessage(group_id=self.id, widget_id=event.button.id))


class EnableDisableTabs(DynamicTabbedContent):
    panel_prefix = "enable_disable_panel"

    def _make_pane_content(self, group_id: str, data: dict[str, NodeStatus], panel_id: str) -> EnableDisablePanel:
        return EnableDisablePanel(data, id=panel_id)
