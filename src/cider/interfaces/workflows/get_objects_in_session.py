import cider.interfaces.actions.actions as ca
from cider.interfaces.actions.action_interfaces import ActionInterface


class GetObjectsInSessionAction(ActionInterface):
    '''
    Complex action, gets all objects of a specific class in a session. This can be refined to search for specific objects
    '''
    
    def action(self, session_dal, applied_class: str, specific_objects=None):
        segment = ca.GetAttributeAction(self._configuration)(session_dal, "segment")
        full_app_list = self._get_segment_apps(segment)
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

    def _get_segment_apps(self, segment):
        '''
        Gets all apps in a segment
        '''
        apps = []

        for ss in ca.GetAttributeAction(self._configuration)(segment, "segments"):
            apps += self._get_segment_apps(ss)

        for aa in ca.GetAttributeAction(self._configuration)(segment, "applications"):
            apps.append(aa)

        return apps
