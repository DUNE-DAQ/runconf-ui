from textual.screen import Screen
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper


class DaqScreen(Screen):
    def __init__(
        self,
        configuration: ConfigurationWrapper,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self._configuration = configuration

    @property
    def configuration(self) -> ConfigurationWrapper:
        return self._configuration
