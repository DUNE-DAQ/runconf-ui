from .adapter import Adapter

from runconf_ui.exceptions import IncompatibleDalException

from conffwk import Configuration
from conffwk.dal import DalBase


class DisableComponent(Adapter):
    def __init__(
        self, configuration: Configuration, session: DalBase, dal: DalBase, label=""
    ):
        super().__init__(configuration, session, label)
        if "Resource" not in configuration.superclasses(dal.className(), all=True):
            raise IncompatibleDalException(
                f"{dal!r} is not of class 'Resource' this means it cannot be trivially enabled/disabled"
            )

        super().__init__(configuration, session, dal)

    def get(self) -> bool:
        return self.dal_enabled()

    def set(self, value: bool) -> None:
        if value and self.dal in self.session.disabled:
            self.session.disabled.remove(self.dal)
        elif not value and self.dal not in self.session.disabled:
            self.session.disabled.append(self.dal)
        self.configuration.update_dal(self.session)
        self.configuration.update_dal(self.dal)

