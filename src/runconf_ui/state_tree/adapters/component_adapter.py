from conffwk import Configuration
from conffwk.dal import DalBase
from confmodel_dal import disable_component, enable_component

from runconf_ui.exceptions import IncompatibleDalException

from .adapter import Adapter


class DisableComponent(Adapter):
    """Adapter that enables/disables Resource DAL objects via component disable state.

    Raises an IncompatibleDalException if the DAL is not a Resource subclass.
    """

    def __init__(
        self,
        configuration: Configuration,
        session: DalBase,
        dal: DalBase,
        label: str = "",
    ):
        """Initialize a DisableComponent adapter.

        :param configuration: The Configuration object containing the DAL
        :param session: The session DAL object
        :param dal: The Resource DAL object to manage
        :param label: Optional label for display purposes
        :raises IncompatibleDalException: If the DAL is not a Resource class
        """
        if "Resource" not in configuration.superclasses(dal.className(), all=True):
            raise IncompatibleDalException(
                f"{dal!r} is not of class 'Resource' this means it cannot be trivially enabled/disabled"
            )
        self.label = label
        super().__init__(configuration, session, dal)

    def get(self) -> bool:
        """Get the enabled state of the component.

        :returns: True if the component is enabled as a resource, False otherwise
        :rtype: bool
        """
        return self.dal_enabled()

    def set(self, value: bool) -> None:
        """Set the enabled state of the component.

        :param value: True to enable the component, False to disable
        """
        if value:
            enable_component(self.configuration._obj, self.session.id, self.dal.id)
        else:
            disable_component(self.configuration._obj, self.session.id, self.dal.id)

        self.configuration.update_dal(self.session)
        self.configuration.update_dal(self.dal)
