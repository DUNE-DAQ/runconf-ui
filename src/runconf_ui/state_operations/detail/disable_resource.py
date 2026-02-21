from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.exceptions import IncompatibleDalException
from runconf_ui.state_operations.state_operation import DisableOperation


class DisableResource(DisableOperation):
    def __init__(
        self, configuration: Configuration, session: DalBase, dal: DalBase, label=""
    ):
        super().__init__(configuration, session, label)
        if "Resource" not in configuration.superclasses(dal.className(), all=True):
            raise IncompatibleDalException(
                f"{dal!r} is not of class 'Resource' this means it cannot be trivially enabled/disabled"
            )

        self.dal = dal

    def _get_state(self) -> bool:
        # Not ideal but it'll do
        return self.dal not in self.session.disabled

    def _set_state(self, state: bool):
        if self.get_state() == state:
            return

        if state and self.dal in self.session.disabled:
            idx = self.session.disabled.index(self.dal)
            self.session.disabled.pop(idx)

        elif not state and self.dal not in self.session.disabled:
            self.session.disabled.append(self.dal)

        self.configuration.update_dal(self.session)
        self.configuration.update_dal(self.dal)