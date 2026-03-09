import re

from textual import on
from textual.containers import ScrollableContainer
from textual.widgets import Button
from .dynamic_panel import DynamicTabbedContent
from textual.css.query import NoMatches

from runconf_ui.state_tree import NodeStatus

from ..messages import NodeToggledMessage

# ---------------------------------------------------------------------------
# Enable/Disable
# ---------------------------------------------------------------------------

class EnableDisablePanel(ScrollableContainer):
    '''
    Scrollable container holding one Button per disableable node.
    Populated via compose() so buttons are mounted with the widget.
    '''
    def __init__(self, nodes: dict[str, NodeStatus], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_nodes = nodes

    def compose(self):
        for node_id, node in self._initial_nodes.items():
            cls     = "node_enabled" if node.is_enabled else "node_disabled"
            enabled = node.is_interactive
            yield Button(
                label=node.node.label,
                id=node_id,
                classes=f"enable_disable_button {cls}",
                disabled=not enabled,
            )

    def update_buttons(self, nodes: dict[str, NodeStatus]):
        for node_id, node in nodes.items():
            cls     = "node_enabled" if node.is_enabled else "node_disabled"
            enabled = node.is_interactive
            try:
                button: Button = self.query_one(f"#{node_id}", Button)
            except NoMatches:
                continue
            button.remove_class("node_enabled", "node_disabled")
            button.add_class(cls)
            button.disabled = not enabled

    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed):
        self.post_message(NodeToggledMessage(group_id=self.id, widget_id=event.button.id))


class EnableDisableTabs(DynamicTabbedContent):
    '''TabbedContent with one EnableDisablePanel per disableable group.'''

    panel_prefix = "enable_disable_panel"

    def _make_pane_content(self, group_id: str, data: dict[str, NodeStatus]) -> EnableDisablePanel:
        return EnableDisablePanel(data)

    def _update_pane(self, panel: EnableDisablePanel, data: dict[str, NodeStatus]) -> None:
        panel.update_buttons(data)
