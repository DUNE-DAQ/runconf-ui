import cider.interfaces.actions.actions as ca
from cider.interfaces.actions.action_interfaces import ActionInterface

class EnableSessionAppAttributeAction(ActionInterface):
    def action(self, session_dal, applied_class: str, attribute_name: str, attribute_value: str, specific_objects=None):
        segment = ca.GetAttributeAction(self._configuration)(session_dal, 'segments')
        
        apps = self._get_segment_apps(segment)
        
        for aa in apps:
            # If we want to change only specific objects, skip the rest
            if specific_objects is not None and aa not in specific_objects:
                continue
            
            roapp = ca.GetDalObjectAction(self._configuration)(applied_class, uid=aa)
            ca.ChangeAttributeAction(self._configuration)(roapp, attribute_name, attribute_value)
            ca.UpdateDalAction(self._configuration)(roapp)
    
    def _get_segment_apps(self, segment):
        apps = []
        for ss in ca.GetAttributeAction(self._configuration)(segment, 'segments'):
            apps += self._get_segment_apps(ss)

        for aa in ca.GetAttributeAction(self._configuration)(segment,'applications'):
            apps.append(aa.id)

        return apps
