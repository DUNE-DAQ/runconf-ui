from conffwk import Configuration
from conffwk.dal import DalBase
from confmodel_dal import component_disabled

from runconf_ui.state_operations.state_operation import DisableOperation
from runconf_ui.exceptions import IncompatibleDalException

class DisableResource(DisableOperation):
    def __init__(self, configuration: Configuration, session: DalBase, dal: DalBase):
        super().__init__(configuration, session)
        if "Resource" not in configuration.superclasses(dal.className(), all=True):
            raise IncompatibleDalException(f"{repr(dal)} is not of class 'Resource' this means it cannot be trivially enabled/disabled")
        
        self.dal = dal
        
    def get_state(self)->bool:
        # Not ideal but it'll do
        return self.dal not in self.session.disabled
    
    def set_state(self, state: bool):
        if self.get_state() == state:
            return
        
        if state and self.dal in self.session.disabled:
            idx = self.session.disabled.index(self.dal)
            self.session.disabled.pop(idx)
        
        elif not state and self.dal not in self.session.disabled:
            self.session.disabled.append(self.dal)
        
        self.configuration.update_dal(self.session)
        self.configuration.update_dal(self.dal)
        
    def __eq__(self, other: 'DisableResource'):
        if not isinstance(other , DisableResource):
            return False
        
        '''
        We can assume (reasonably that they are the same if the ids match)
        '''
        return other.dal.id == self.dal.id and other.session.id == self.session.id
    
