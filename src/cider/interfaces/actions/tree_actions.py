from cider.interfaces.actions.action_interfaces import (
    ActionInterface,
    TreeActionInterface,
)
import cider.interfaces.actions.actions as ca
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper

"""
Whist tree action interface is quite generic, it's useful to have some non-generic actions
"""


class GetRelationshipTree(TreeActionInterface):
    def __init__(self, configuration: ConfigurationWrapper):
        super().__init__(configuration, ca.GetRelatedDalsAction)


class GetClassRelations(TreeActionInterface):
    def __init__(self, configuration: ConfigurationWrapper):
        super().__init__(configuration, ca.GetRelatedDalsAction)
