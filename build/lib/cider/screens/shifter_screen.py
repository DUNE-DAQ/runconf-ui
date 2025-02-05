'''
Delete me when done with
'''

from textual.screen import Screen
from textual.widgets import Switch, Static
from textual.containers import Horizontal

from cider.widgets.daq_widget import DaqWidget
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.interfaces.actions.actions import (GetDalsOfClassAction,
                                              DisableDalAction,
                                              UpdateDalAction,
                                              CommitConfigurationAction,
                                              GetDalObjectAction)

class ShifterScreen(Screen):
    # Okay lets go
    
    def __init__(self, configuration: ConfigurationWrapper, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name, id, classes)
        
        self._configuration = configuration

        # Get objects we want to display
        self.disable_objs = GetDalsOfClassAction(self._configuration)("Component")


        self.switches = []
        # Generate a switch
        for obj in self.disable_objs:
            self.switches.append(self.generate_switch(getattr(obj,'id'), getattr(obj,'id'), False))

    def generate_switch(self, object_name: str, switch_label: str, is_switched_on: bool=True):
        
        my_widget = DaqWidget(
            self._configuration,
            Switch(id=f"switch_{object_name}",
                   value=is_switched_on),
                    object_name,
                    id=f"{object_name}",)
        
        my_widget.add_action_sequence("switch_changed", [DisableDalAction(self._configuration)])
        
        return Horizontal(
            # Static(f"{switch_label}                    ", classes="label"),
            my_widget,
            classes='container',
        )
        
    def on_switch_changed(self, event: Switch.Changed):
        # Get the object
        obj_name = event.switch.id
        disable_value = event.switch.value
        
        # Get the object index
        obj_name_dal = obj_name.replace("switch_", "")
        obj = [o for o in self.disable_objs if getattr(o,'id') == obj_name_dal][0]

        # Disable the object
        switch_to_query: DaqWidget = self.query_one(f"#{obj_name_dal}")
        switch_to_query.do_action_sequence("switch_changed", dal=obj, session_name="fakedata-session", disable=disable_value)
        UpdateDalAction(self._configuration)(GetDalObjectAction(self._configuration)("fakedata-session", "Session"))
        CommitConfigurationAction(self._configuration)("lol")

    def compose(self):
        yield from self.switches


