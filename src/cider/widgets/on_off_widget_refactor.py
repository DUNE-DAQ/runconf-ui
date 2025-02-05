"""
HW: Widget that contains a grid of things to turn on and off
"""

from textual.widgets import Switch, Static
from textual.containers import Grid, Vertical, ScrollableContainer

from cider.widgets.daq_widget import DaqWidget
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.interfaces.actions.actions import (
    GetDalsOfClassAction,
    GetDalObjectAction,
    GetAttributeAction,
    DisableDalAction,
    GetClassNameAction,
)
from cider.interfaces.actions.action_interfaces import ActionInterface

from functools import partial
from typing import Dict, List, Any, Callable


class OnOffGridWidget(DaqWidget):
    def __init__(
        self,
        configuration: ConfigurationWrapper,
        switch_labels: Dict[str, bool] ,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(configuration, None, name, id, classes, disabled)
        
        self.switches = {label: self.generate_switch(label, enabled) for label, enabled in switch_labels.items()}
            
        self.grouped_objs = {"Properties": list(self.switches.keys())}
    
    def group_objs(self, group_method: Callable):
        self.grouped_objs = {}
        # Group objects with some callable grouping method, typically an action
        for lab in self.switches.keys():
            group_name = group_method(lab)

            if group_name not in self.grouped_objs:
                self.grouped_objs[group_name] = {"labels": []}

            self.grouped_objs[group_name]["labels"].append(lab)

    
    def generate_switch(self, label: str, is_switched_on: bool = True):
        switch_widget = DaqWidget(
            self._configuration,
            Switch(
                id=f"{label}_switch",
                value=is_switched_on,
            ),
            label,
            id=label,
        )
        
        status_widget = Static(
            (
                "[bold green]ENABLED ✅[/bold green]"
                if is_switched_on
                else "[bold grey46]DISABLED 🛑"
            ),
            id=f"{label}_status",
            classes="label",
        )

        # Get all the labels
        return [
            Static(f"[bold magenta]{label} [/bold magenta]", classes="label"),
            switch_widget,
            status_widget,
        ]

    
    def set_switch_action(self, button_label: str, action: Callable):
        if button_label in self.switches:
            self.switches[button_label][1].add_action_sequence("switch_changed", [action])
    
    def on_switch_changed(self, event: Switch.Changed):

        # Get the object
        obj_name = event.switch.id
        disable_value = not event.switch.value

        # Get the object index
        obj_name_dal = obj_name.replace("_switch", "")

        # Disable the object
        switch_to_query: DaqWidget = self.query_one(f"#{obj_name_dal}")
        switch_to_query.do_action_sequence(
            "switch_changed", disable=disable_value
        )

        status_widget: Static = self.query_one(f"#{obj_name_dal}_status")
        status_widget.update(
            "[bold green]ENABLED ✅[/bold green]"
            if event.switch.value
            else "[bold grey46]DISABLED 🛑"
        )



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

                for group_name, labels in self.grouped_objs.items():
                    # Add a header for the class name
                    yield Static(
                        f"[bold cyan]{group_name}[/bold cyan]", classes="class-header"
                    )

                    # Create a grid for the objects in this class
                    # This is far far too nested...
                    with Grid():
                        for l in labels:
                            for widgets in self.switches[l]:
                                for w in widgets: 
                                    yield w
                                    
class DisableComponentWidget(OnOffGridWidget):
    def __init__(
        self,
        configuration: ConfigurationWrapper,
        session_name: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        
        # Okay now we get the widgets
        disableable_objs = GetDalsOfClassAction(configuration)("Component")
        disabled_objs  = GetAttributeAction(configuration)(GetDalObjectAction(self._configuration)(session_name, "Session"), "disabled")
        
        label_dict = {GetAttributeAction(configuration)(obj, "id") :
                        obj in  disabled_objs
                        for obj in disableable_objs}
        
        super().__init__(configuration, label_dict, name, id, classes, disabled)
        
        # Setup disable/enable aactions
        for label, dal in zip(label_dict.keys(), disabled_objs):
            full_action_class = DisableDalAction(configuration)
            partial_action = partial(full_action_class, dal=dal, session_name=session_name)
            
            self.set_switch_action(label, partial_action)
            
        # Finally we group objects
        group_callable = lambda x: GetClassNameAction(configuration)()
        
class DisableAttrWidget(OnOffGridWidget):
    def __init__(self, configuration: ConfigurationWrapper, attr_list: List[str], object_classes: List[str], name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False) -> None:
        
        

        super().__init__(configuration, switch_labels, name, id, classes, disabled)