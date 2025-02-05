'''
Delete me when done with
'''

from textual.screen import Screen
from textual.widgets import Switch, Static, Header, Footer, Button
from textual.containers import Grid, Vertical

from cider.widgets.daq_widget import DaqWidget
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.interfaces.actions.actions import (GetDalsOfClassAction,
                                              DisableDalAction,
                                              UpdateDalAction,
                                              CommitConfigurationAction,
                                              GetDalObjectAction)

class DisableObjectScreen(Screen):
    # Okay lets go
    CSS_PATH="toggle_screen.tcss"
    
    def __init__(self, configuration: ConfigurationWrapper, session: str, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name, id, classes)

        self._configuration = configuration
        # Get objects we want to display
        self.disableable_objs = GetDalsOfClassAction(self._configuration)("Component")

        self.session=session

        # Gonna enable literally everything
        self.disabled_objs = getattr(GetDalObjectAction(self._configuration)(self.session, "Session"), "disabled")        

    def generate_switch(self, object_name: str, switch_label: str, is_switched_on: bool=True):

        my_widget = DaqWidget(
            self._configuration,
            Switch(id=f"switch_{switch_label}",
                   value = is_switched_on),
                    object_name,
                    id=f"{object_name}",
                )

        my_widget.add_action_sequence("switch_changed", [DisableDalAction(self._configuration)])
        
        return Grid(
            Static(f"[bold magenta]{object_name} [/bold magenta] [dim magenta]:[/dim magenta]  ", classes="label"),
            my_widget,
        )
        
    def on_switch_changed(self, event: Switch.Changed):
        # Get the object
        obj_name = event.switch.id
        disable_value = not event.switch.value
        
        # Get the object index
        obj_name_dal = obj_name.replace("switch_", "")
        obj = [o for o in self.disableable_objs if getattr(o,'id') == obj_name_dal][0]

        # Disable the object
        switch_to_query: DaqWidget = self.query_one(f"#{obj_name_dal}")
        switch_to_query.do_action_sequence("switch_changed", dal=obj, session_name=self.session, disable=disable_value)
        UpdateDalAction(self._configuration)(GetDalObjectAction(self._configuration)(self.session, "Session"))


    def on_button_pressed(self, event: Button.Pressed):
        CommitConfigurationAction(self._configuration)("")

    def compose(self):
        for obj in self.disableable_objs:
            is_enabled = obj not in self.disabled_objs            
            yield self.generate_switch(getattr(obj,'id'), getattr(obj,'id'), is_enabled)
        
        yield Button("Commit", id="commit_button", variant="success")
        
        yield Header()
        yield Footer()