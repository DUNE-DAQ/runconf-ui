from conffwk import Configuration
from conffwk.dal import DalBase
from confmodel_dal import disable_component, enable_component

from runconf_ui.exceptions import IncompatibleDalException

from .adapter import Adapter


class DisableComponent(Adapter):
    def __init__(
        self, configuration: Configuration, session: DalBase, dal: DalBase, label: str = ""
    ):
        if "Resource" not in configuration.superclasses(dal.className(), all=True):
            raise IncompatibleDalException(
                f"{dal!r} is not of class 'Resource' this means it cannot be trivially enabled/disabled"
            )
        self.label = label
        super().__init__(configuration, session, dal)

    def get(self) -> bool:
        return self.dal_enabled()

    def set(self, value: bool) -> None:
        if value:
            enable_component(self.configuration._obj, self.session.id, self.dal.id)
        else:
            disable_component(self.configuration._obj, self.session.id, self.dal.id)
        
        self.configuration.update_dal(self.session)
        self.configuration.update_dal(self.dal)