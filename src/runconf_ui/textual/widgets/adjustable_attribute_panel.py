from textual import on
from textual.containers import ScrollableContainer
from textual.widgets import Button, Input, Static

from runconf_ui.state_tree import NodeStatus

from ..messages import ValueChangedMessage
from .dynamic_panel import DynamicTabbedContent, textual_safe_id


class AdjustableAttributeContainer(Static):
    '''
    Container for a single adjustable attribute
    '''
    def __init__(self, node: NodeStatus, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._adjust_node = node
        self._init_value = self._adjust_node.node.get()
        
    def compose(self):
        node_label = self._adjust_node.label
        curr_val = self._adjust_node.value

        if isinstance(curr_val, float):
            curr_val = f"{curr_val:3f}"

        label_widget = Static(
            f"[bold]ID:[/bold] [bold red]{node_label}[/bold red]:",
            id="label",
            classes="adjustable-attribute-label adjustable-attribute-name",
            disabled=not self.interactive,
        )
        if self._adjust_node.tooltip:
            label_widget.tooltip = self._adjust_node.tooltip

        with ScrollableContainer(id=f"{self.id}_container", classes="adjustable_container",):
            yield label_widget
            
            yield Input(
                value=f"{curr_val}",
                placeholder=f"{curr_val}",
                id="input",
                classes="adjustable-attribute-input",
                disabled=not self.interactive,
            )

            yield Button(
                "Apply",
                id="apply",
                classes="adjustable-attribute-button",
                variant="primary",
                disabled=not self.interactive,
            )

            yield Button(
                "Reset",
                id="reset",
                classes="adjustable-attribute-button",
                variant="warning",
                disabled=not self.interactive,
            )
            
    def _handle_value_changed(self, new_value):
        self.post_message(ValueChangedMessage(self._adjust_node.path, new_value))

    @on(Button.Pressed, "#reset")
    def handle_reset(self, _):
        input = self.query_one(Input)        
        input.clear()
        input.insert_text_at_cursor(f"{self._init_value}")
        self._handle_value_changed(self._init_value)

    @on(Button.Pressed, "#apply")
    def handle_apply(self, _):
        input = self.query_one(Input)
        self._handle_value_changed(input.value)
        
    def update_node(self, node: NodeStatus):
        self._adjust_node = node
        input = self.query_one(Input)
        input.insert_text_at_cursor(f"{self._adjust_node.value}")

    @property
    def interactive(self):
        return self._adjust_node.is_interactive

    def check_enabled(self):
        container = self.query_one(ScrollableContainer)
        for child in container.children:
            if not hasattr(child, 'disabled'):
                continue
            child.disabled = not self.interactive
            
class AdjustableAttributePanel(ScrollableContainer):
    def __init__(self, group_id: str, nodes: dict[str, NodeStatus], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._group_id = group_id
        self._runconf_nodes = nodes
    
    def compose(self):
        for node_id, node in self._runconf_nodes.items():
            yield AdjustableAttributeContainer(
                node,
                id=textual_safe_id(node_id),
                classes="adjustable_attribute",
            )

    def update_containers(self, nodes: dict[str, NodeStatus])->None:
        for node_id in nodes:
            safe_id = textual_safe_id(node_id)
            results = self.query(f"#{safe_id}")
            if not results:
                continue
            container = results.first(AdjustableAttributeContainer)
            container.check_enabled()
            
class AdjustableAttributeTabs(DynamicTabbedContent):
    panel_prefix = "adjustable_panel"

    def _make_pane_content(self, group_id: str, data: dict[str, NodeStatus], panel_id: str) -> AdjustableAttributePanel:
        return AdjustableAttributePanel(group_id, data, id=panel_id)

    def _update_panes(self, data: dict) -> None:
        for group_id, nodes in data.items():
            group_id_safe = textual_safe_id(group_id)
            panel_id      = self._panel_id(group_id_safe)
            results = self.query(f"#{panel_id}")
            if not results:
                continue
            panel = results.first(AdjustableAttributePanel)
            panel.update_containers(nodes)