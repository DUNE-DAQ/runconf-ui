from conffwk import Configuration
from conffwk.dal import DalBase
from confmodel_dal import exclude_entity, include_entity

from runconf_ui.exceptions import IncompatibleDalException

from .adapter import Adapter


class ExcludableEntityAdapter(Adapter):
    """Adapter that includes/excludeds ExcludableEntity DAL objects via component excluded state.

    Raises an IncompatibleDalException if the DAL is not a ExcludableEntity subclass.
    """

    def __init__(
        self,
        configuration: Configuration,
        session: DalBase,
        dal: DalBase,
        label: str = "",
    ):
        """Initialize a ExcludableEntityAdapter adapter.

        :param configuration: The Configuration object containing the DAL
        :param session: The session DAL object
        :param dal: The ExcludableEntity DAL object to manage
        :param label: Optional label for display purposes
        :raises IncompatibleDalException: If the DAL is not a ExcludableEntity class
        """
        if "ExcludableEntity" not in configuration.superclasses(dal.className(), all=True):
            raise IncompatibleDalException(
                f"{dal!r} is not of class 'ExcludableEntity' this means it cannot be trivially excluded/included"
            )
        self.label = label
        super().__init__(configuration, session, dal)

    def get(self) -> bool:
        """Get the enabled state of the component.

        :returns: True if the component is enabled as a ExcludableEntity, False otherwise
        :rtype: bool
        """
        return self.dal_included()

    def set(self, value: bool) -> None:
        """Set the enabled state of the component.

        :param value: True to include the component, False to exclue
        """
        if value:
            include_entity(self.configuration._obj, self.session.id, self.dal.id)
        else:
            exclude_entity(self.configuration._obj, self.session.id, self.dal.id)
