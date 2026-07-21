from textual import on
from textual.containers import ScrollableContainer
from textual.widgets import Button, Input, Static

from runconf_ui.state_tree import NodeStatus
from runconf_ui.utils import get_logger

from ..messages import ValueChangedMessage
from .dynamic_panel import DynamicTabbedContent, textual_safe_id


class AdjustableAttributeContainer(Static):
    """Container widget for displaying and editing a single adjustable attribute.

    Displays the attribute name, current value in an input field, and Apply/Reset
    buttons. Handles user input and emits ValueChangedMessage when values change.
    """

    def __init__(self, group_id: str, node: NodeStatus, *args, **kwargs):
        """Initialize AdjustableAttributeContainer.

        :param group_id: The ID of the group containing the adjustable attribute
        :param node: The NodeStatus object representing the adjustable attribute
        :param args: Variable positional arguments passed to parent Static
        :param kwargs: Variable keyword arguments passed to parent Static
        """
        super().__init__(*args, **kwargs)
        self._adjust_node = node
        self._group_id = group_id
        self._curr_value = self._init_value = self._adjust_node.node.get()

    def compose(self):
        """Compose the attribute container with label, input, and buttons.

        :returns: A generator yielding child widgets
        """
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

        with ScrollableContainer(
            id=f"{self.id}_container", classes="adjustable_container"
        ):
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

            yield Static(
                self._generate_current_value_text(),
                id="current_value",
                classes="adjustable-attribute-current-value",
                disabled=not self.interactive,
            )

    def on_mount(self) -> None:
        self.border_title = self._adjust_node.tooltip

    def _handle_value_changed(self, new_value):
        """Emit a ValueChangedMessage for the new attribute value.

        :param new_value: The new value entered by the user
        """
        self._curr_value = new_value
        self.query_one("#current_value", Static).update(
            self._generate_current_value_text()
        )
        self.post_message(
            ValueChangedMessage(self._group_id, self._adjust_node.path, new_value)
        )

    def _generate_current_value_text(self) -> str:
        """Generate the display text for the current value.

        :returns: A formatted string representing the current value
        """
        return (
            f"[dim purple]Current Value: [/][bold red]{self._curr_value}[/bold red]\n"
            f"[dim grey]Init value: [/][dim red]{self._init_value}[/]"
        )

    @on(Button.Pressed, "#reset")
    def handle_reset(self, _):
        """Handle reset button press - revert to initial value.

        :param _: The Button.Pressed event (unused)
        """
        self.query_one(Input).value = str(self._init_value)
        self._handle_value_changed(self._init_value)

    @on(Button.Pressed, "#apply")
    def handle_apply(self, _):
        """Handle apply button press - commit the new value.

        :param _: The Button.Pressed event (unused)
        """
        self._handle_value_changed(self.query_one(Input).value)

    def update_node(self, node: NodeStatus):
        """Update the displayed node to a new NodeStatus.

        :param node: The new NodeStatus to display
        """
        self._adjust_node = node
        self.check_enabled()

    @property
    def interactive(self):
        """Check if this attribute container can be interacted with.

        :returns: True if the node is interactive, False otherwise
        :rtype: bool
        """
        return self._adjust_node.is_interactive

    def check_enabled(self):
        """Update widget disabled state based on interactivity.

        Called to refresh the enabled/disabled state of all child widgets
        based on the node's current interactivity.
        """
        container = self.query_one(ScrollableContainer)
        for child in container.children:
            get_logger().debug(f"Setting {child.id} to {not self.interactive}")
            if hasattr(child, "disabled"):
                child.disabled = not self.interactive


class AdjustableAttributePanel(ScrollableContainer):
    """Panel widget displaying adjustable attribute controls for a group of nodes.

    This widget displays a scrollable container of AdjustableAttributeContainers,
    one for each adjustable attribute in a node group.
    """

    def __init__(self, group_id: str, nodes: dict[str, NodeStatus], *args, **kwargs):
        """Initialize AdjustableAttributePanel.

        :param group_id: The identifier for this panel's node group
        :param nodes: Dictionary mapping node IDs to their current NodeStatus
        :param args: Variable positional arguments passed to parent ScrollableContainer
        :param kwargs: Variable keyword arguments passed to parent ScrollableContainer
        """
        super().__init__(*args, **kwargs)
        self._group_id = group_id
        self._runconf_nodes = nodes

    def compose(self):
        """Compose adjustable attribute containers for all nodes in this group.

        :returns: A generator yielding AdjustableAttributeContainer widgets
        """
        for node_id, node in self._runconf_nodes.items():
            yield AdjustableAttributeContainer(
                self._group_id,
                node,
                id=textual_safe_id(node_id),
                classes="adjustable_attribute",
            )

    def update_containers(self, nodes: dict[str, NodeStatus]) -> None:
        """Update all attribute containers with new node status data.

        Updates the enabled/disabled state of containers based on node interactivity.

        :param nodes: Dictionary mapping node IDs to their current NodeStatus
        """
        for node_id, node in nodes.items():
            safe_id = textual_safe_id(node_id)
            results = self.query(f"#{safe_id}")
            if not results:
                continue
            results.first(AdjustableAttributeContainer).update_node(node)


class AdjustableAttributeTabs(DynamicTabbedContent):
    """Tabbed widget containing adjustable attribute panels for multiple groups.

    This widget manages multiple AdjustableAttributePanel tabs, one for each group
    of adjustable attributes in the configuration.
    """

    panel_prefix = "adjustable_panel"

    def _make_pane_content(
        self, group_id: str, data: dict[str, NodeStatus], panel_id: str
    ) -> AdjustableAttributePanel:
        """Create an AdjustableAttributePanel for the given group.

        :param group_id: The identifier for this group
        :param data: Dictionary of adjustable nodes in this group
        :param panel_id: The widget ID to assign to the panel
        :returns: A new AdjustableAttributePanel widget
        :rtype: AdjustableAttributePanel
        """
        return AdjustableAttributePanel(group_id, data, id=panel_id)

    def _update_panes(self, data: dict) -> None:
        """Update all adjustable attribute panes with new node status data.

        :param data: Dictionary mapping group IDs to node dictionaries
        """
        for group_id, nodes in data.items():
            group_id_safe = textual_safe_id(group_id)
            panel_id = self._panel_id(group_id_safe)
            results = self.query(f"#{panel_id}")
            if not results:
                continue
            results.first(AdjustableAttributePanel).update_containers(nodes)
