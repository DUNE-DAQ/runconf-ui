from cider.interfaces.actions.action_interfaces import ActionInterface, TreeActionInterface
import cider.interfaces.actions.actions as ca
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper

"""
Whist tree action interface is quite generic, it's useful to have some non-generic actions
"""
class GetRelationshipTree(TreeActionInterface):
    def __init__(self, configuration: ConfigurationWrapper, action: ca.GetRelatedDalsAction):
        super().__init__(configuration, action)
    
class GetClassRelations(TreeActionInterface):
    def __init__(self, configuration: ConfigurationWrapper, action: ca.GetDalsOfClassAction):
        super().__init__(configuration, action)
