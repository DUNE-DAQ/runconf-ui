"""
HW: Widget that contains a list of things to turn on and off
"""

from cider.widgets.daq_widget import DaqWidget
from textual.widgets import Switch, Static
from textual.containers import Grid, Vertical, ScrollableContainer

from cider.widgets.daq_widget import DaqWidget
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.interfaces.actions.actions import (
    GetDalsOfClassAction,
    GetDalObjectAction,
    GetAttributeAction,
    GetClassNameAction,
)

from typing import List, Any, Callable


class OnOffGridWidget(DaqWidget):
    def __init__(
        self,
        configuration: ConfigurationWrapper,
        object_list: List[Any],
        label_list: List[List[str]],
        enable_disable_attr: str | List[str],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(configuration, None, name, id, classes, disabled)

        if len(object_list) != len(label_list):
            raise ValueError("Object list and label list must be the same length")

        self.object_list = object_list
        self.label_list = label_list
        self.enable_disable_attr = enable_disable_attr

        self.grouped_objs = {"AllObjects": object_list}

        self.switched_off_objs: List[bool] = []

    def group_objs(self, group_method: Callable):
        self.grouped_objs = {}

        # Group objects with some callable grouping method, typically an action
        for obj, lab in zip(self.object_list, self.label_list):
            group_name = group_method(obj)

            if group_name not in self.grouped_objs:
                self.grouped_objs[group_name] = {"objs": [], "labels": []}

            self.grouped_objs[group_name]["objs"].append(obj)
            self.grouped_objs[group_name]["labels"].append(lab)

    def initialise_disabled_objs(self, off_check: Callable):
        self.switched_off_objs = [o for o in self.object_list if off_check(o)]

    def generate_switch(self, object_labels: List[str], is_switched_on: bool = True):
        my_widget = DaqWidget(
            self._configuration,
            Switch(
                id=f"{object_labels[0]}_switch",
                value=is_switched_on,
            ),
            object_labels[0],
            id=f"{object_labels[0]}",
        )

        status_widget = Static(
            (
                "[bold green]ENABLED ✅[/bold green]"
                if is_switched_on
                else "[bold grey46]DISABLED 🛑"
            ),
            id=f"{object_labels[0]}_status",
            classes="label",
        )

        # Get all the labels
        return (
            [
                Static(f"[bold magenta]{lbl} [/bold magenta]", classes="label")
                for lbl in object_labels
            ],
            my_widget,
            status_widget,
        )

    def on_switch_changed(self, event: Switch.Changed):
        # Do nothing if there is no action sequence
        if "switch_changed" not in self._actions:
            return

        # Get the object
        obj_name = event.switch.id
        disable_value = not event.switch.value

        # Get the object index
        obj_name_dal = obj_name.replace("_switch", "")
        obj = [
            o for o in self.object_list if self.get_attribute(o, "id") == obj_name_dal
        ][0]

        # Disable the object
        switch_to_query: DaqWidget = self.query_one(f"#{obj_name_dal}")

        switch_to_query.do_action_sequence(
            "switch_changed", obj, self.enable_disable_attr, disable=disable_value
        )

        # Update the status text based on the switch value
        status_widget: Static = self.query_one(f"#{obj_name_dal}_status")
        status_widget.update(
            "[bold green]ENABLED ✅[/bold green]"
            if event.switch.value
            else "[bold grey46]DISABLED 🛑"
        )

    def compose(self):
        # Okay we can sort by class id's

        with Vertical(id="main_container"):
            yield Static(
                "[bold deep_pink3]Toggleable Components", classes="table-header"
            )

            with ScrollableContainer(id="main_interface"):

                for group_name, objs in self.grouped_objs.items():
                    # Add a header for the class name
                    yield Static(
                        f"[bold cyan]{group_name}[/bold cyan]", classes="class-header"
                    )

                    # Create a grid for the objects in this class
                    with Grid():
                        for proper_obj, obj_labels in zip(objs["objs"], objs["labels"]):

                            labels, switch, status = self.generate_switch(
                                obj_labels, proper_obj not in self.switched_off_objs
                            )
                            for label in labels:
                                yield label
                            yield switch
                            yield status


# For ease of use, we can define a couple of derived widgets
class DisableObjectWidget(OnOffGridWidget):
    def __init__(
        self,
        configuration: ConfigurationWrapper,
        session_name: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:

        # A bit hacky but makes screen app cleaner
        disableable_objs = GetDalsOfClassAction(configuration)("Component")
        label_list = [
            [GetAttributeAction(configuration)(obj, "id")] for obj in disableable_objs
        ]

        super().__init__(
            configuration,
            disableable_objs,
            label_list,
            session_name,
            name,
            id,
            classes,
            disabled,
        )

        # Here we can just initialise everything in the usual way
        self.group_objs(GetClassNameAction(self._configuration))

        self.switched_off_objs = self.get_attribute(
            GetDalObjectAction(self._configuration)(session_name, "Session"), "disabled"
        )
