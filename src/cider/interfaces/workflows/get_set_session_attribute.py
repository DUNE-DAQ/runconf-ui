import cider.interfaces.actions.actions as ca
from cider.interfaces.actions.action_interfaces import ActionInterface
from cider.interfaces.workflows.get_objects_in_session import GetObjectsInSessionAction


class SetAttributeValueSessionAction(ActionInterface):
    """
    Sets the value of an attribute of objects (or a subset) in Session
    """

    def action(
        self,
        session_dal,
        applied_class: str,
        attribute_name: str,
        attribute_value: str,
        specific_objects=None,
    ):

        apps = GetObjectsInSessionAction(self._configuration).action(
            session_dal, applied_class, specific_objects
        )

        for roapp in apps:
            # If we want to change only specific objects, skip the rest
            ca.ChangeAttributeAction(self._configuration)(
                roapp, attribute_name, attribute_value
            )
            ca.UpdateDalAction(self._configuration)(roapp)
            ca.UpdateDalAction(self._configuration)(session_dal)


class GetAttributeValueSessionAction(ActionInterface):
    """
    Gets the value of an attribute of objects (or a subset) in Session
    """

    def action(
        self,
        session_dal,
        applied_class: str,
        attribute_name: str,
        specific_objects=None,
    ):
        apps = GetObjectsInSessionAction(self._configuration).action(
            session_dal, applied_class, specific_objects
        )

        return [
            ca.GetAttributeAction(self._configuration)(roapp, attribute_name)
            for roapp in apps
        ]
