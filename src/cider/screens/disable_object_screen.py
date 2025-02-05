from textual.screen import Screen
from textual.widgets import Header, Footer, Button

from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.interfaces.actions.actions import (
    GetDalsOfClassAction,
    CommitConfigurationAction,
    GetAttributeAction,
    DisableDalAction,
    UpdateDalAction,
)


from cider.widgets.on_off_grid_widget import DisableObjectWidget, OnOffGridWidget


class DisableObjectScreen(Screen):
    # Okay lets go
    CSS_PATH = "toggle_screen.tcss"

    def __init__(
        self,
        configuration: ConfigurationWrapper,
        session: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)

        self._configuration = configuration
        # Get objects we want to display
        self.disableable_objs = GetDalsOfClassAction(self._configuration)("Component")

        self.session = session

        self.get_attribute = GetAttributeAction(self._configuration)

    def on_button_pressed(self, event: Button.Pressed):
        CommitConfigurationAction(self._configuration)("")

    def compose(self):
        # Okay we can sort by class id's

        disable_obj =  DisableObjectWidget(self._configuration, self.session)
        disable_obj.add_action_sequence("switch_changed", [DisableDalAction(self._configuration), UpdateDalAction(self._configuration)])        
        yield disable_obj

        yield Button("Save Local", id="commit_button", variant="success")

        yield Header()
        yield Footer()

