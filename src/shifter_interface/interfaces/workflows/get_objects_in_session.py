import cider.interfaces.actions.actions as ca
from cider.interfaces.actions.action_interfaces import ActionInterface


class GetSegmentAppsListAction(ActionInterface):
    def action(self, segment):
        """
        Gets all apps in a segment
        """
        apps_list_flat = []

        # Loop over all segments
        for ss in ca.GetAttributeAction(self._configuration)(segment, "segments"):
            apps_list_flat += self.action(ss)

        # loop over all attributes
        for aa in ca.GetAttributeAction(self._configuration)(segment, "applications"):
            apps_list_flat.append(aa)

        return apps_list_flat


class GetObjectsInSessionAction(ActionInterface):
    """
    Complex action, gets all objects of a specific class in a session. This can be refined to search for specific objects
    """

    def action(self, session_dal, applied_class: str, specific_objects=None):
        # Session contains a single segement
        segment = ca.GetAttributeAction(self._configuration)(session_dal, "segment")
        # Get all apps+segments in the segment
        full_app_list = GetSegmentAppsListAction(self._configuration)(segment)

        apps = []
        for app in full_app_list:
            # Check if we have some subset of object
            if (
                specific_objects is not None
                and ca.GetAttributeAction(self._configuration)(app, "id")
                not in specific_objects
            ):
                continue
            # Check if the object is of the right class
            if ca.GetClassNameAction(self._configuration)(app) != applied_class:
                continue
            apps.append(app)
        return apps
