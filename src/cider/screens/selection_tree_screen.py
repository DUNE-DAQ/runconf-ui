from textual.screen import Screen
from textual.widgets import Tree

from cider.widgets.daq_widget import DaqWidget
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.interfaces.actions.actions import (
    GetDalsOfClassAction,
    DisableDalAction,
    UpdateDalAction,
    CommitConfigurationAction,
    GetDalObjectAction,
    GetRelatedDalsAction,
)
from cider.widgets.daq_tree_widget import DaqTreeWidget
from cider.interfaces.actions.tree_actions import GetRelationshipTree


class SelectionTreeScreen(Screen):
    def __init__(
        self,
        configuration: ConfigurationWrapper,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)

        self._configuration = configuration
        self._top_level = {
            "Sessions": GetDalsOfClassAction(self._configuration)("Session")
        }

        self._tree = DaqTreeWidget(
            self._configuration,
            builder_action=GetRelatedDalsAction,
            initial_nodes=self._top_level,
        )

    def on_node_selected(self, event: Tree.NodeSelected):
        raise Exception(event.node.data)

    def compose(self):
        yield self._tree
