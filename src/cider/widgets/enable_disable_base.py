from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
import cider.interfaces.actions.actions as ca

from textual.visual import SupportsVisual
from textual.widgets import Static, Placeholder, Button
from textual.containers import Grid, ScrollableContainer

from typing import List


class __EnableDisablePanel(Static):
    
    '''
    Base class for all of the enable/disable button panel
    '''
    
    def __init__(
        self,
        configuration: ConfigurationWrapper | None,
        session_name: str | None,
        content: str | SupportsVisual = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            content,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

        self._configuration = configuration
        self._session_name = session_name
        self._button_list = self.generate_button_list()

    @property
    def configuration(self) -> ConfigurationWrapper | None:
        return self._configuration

    @configuration.setter
    def configuration(self, configuration: ConfigurationWrapper | None):
        self._configuration = configuration
        try:
            self._button_list = self.generate_button_list()
            self.refresh(recompose=True)
        except Exception as e:
            raise e

    @property
    def session_name(self) -> str | None:
        return self._session_name

    @session_name.setter
    def session_name(self, session_name: str):
        try:
            self._session_name = session_name
            self._button_list = self.generate_button_list()
            self.refresh(recompose=True)
        except Exception as e:
            raise e

    def open_new_session(self, configuration: ConfigurationWrapper, session_name: str):
        self._session_name = session_name
        self._configuration = configuration
        self._button_list = self.generate_button_list()
        self.refresh(recompose=True)

    def check_is_disabled(self, button: str, information: str | List[str]) -> bool:
        return True

    def compose(self):
        with Grid(id="detector_subsystem_panel_grid"):
            with ScrollableContainer(id="buttons_panel"):
                for button, information in self._button_list.items():

                    if self.check_is_disabled(button, information):
                        name_str = f"{button} (Disabled)"
                        classes = "detector_subsystem_button detector_subsystem_button_disabled"

                    else:
                        name_str = f"{button} (Enabled)"
                        classes = "detector_subsystem_button detector_subsystem_button_enabled"

                    id_name = button.replace(" ", "_")

                    yield Button(name_str, id=f"{id_name}_button", classes=classes)

            yield Placeholder("Schematic View", id="schematic_view")

    def generate_button_list(self):
        return {}
