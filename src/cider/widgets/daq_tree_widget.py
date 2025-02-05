"""
Tree structures require a lot more care than most daq widgets, hence the need for a separate class.
"""

from cider.widgets.daq_widget import DaqWidget
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.interfaces.actions.actions import (
    GetDalsOfClassAction,
    DisableDalAction,
    UpdateDalAction,
    GetDalObjectAction,
    GetAttributeAction,
    GetClassNameAction,
)

from cider.interfaces.actions.action_interfaces import (
    TreeActionInterface,
    ActionInterface,
)
from cider.utils.configuration_utils import (
    print_confobj_enabled,
    print_confobj_disabled,
)


from textual.widgets import Tree


class DaqTreeWidget(DaqWidget):
    def __init__(
        self,
        configuration: ConfigurationWrapper,
        builder_action: type[ActionInterface],
        renderable="",
        initial_nodes: dict | None = None,
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        # requires node builder action at initialisation
        super().__init__(
            configuration,
            Tree("Configuration Tree"),
            renderable,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

        self._builder_action = builder_action(configuration)

        if initial_nodes:
            self.build_tree(initial_nodes)

    def build_tree(self, initial_nodes):
        self._widget.clear()

        tree_root = self._widget.root

        # Now we expand
        tree_root.expand()

        for key, branch in initial_nodes.items():
            tree_node = tree_root.add(f"[green]{key}[/green]", expand=False)
            self.__build_tree_node(
                tree_node, self._builder_action(branch), is_disabled=False
            )

    def __build_tree_node(self, input_node, input_list, is_disabled):

        # Just remove the node, ends the recursion
        if len(input_list) == 0:
            input_node.remove()
            return

        for config_item in input_list:
            # Okay now we can deal with dictionary-type inputs
            if isinstance(config_item, dict):
                # Get the key and the objects
                config_key = list(config_item.keys())[0]
                config_objects = list(config_item.values())[0]

                # Check if it's just a string
                if isinstance(config_key, str):
                    dal_str = config_key
                    stored_data = None

                # Now we can deal with the actual objects
                else:
                    dal_str = print_confobj_enabled(config_key)
                    stored_data = config_key

                # Add the node
                tree_node = input_node.add(dal_str, data=stored_data)
                self.__build_tree_node(tree_node, config_objects, is_disabled)
            else:
                input_node.add_leaf(
                    print_confobj_enabled(config_item), data=config_item
                )
