from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.exceptions import CiderBadActionException

from abc import ABC, abstractmethod
from typing import Any

# The idea here is to define an interface for actions on a configuration,
# currently this is very simple but there is scope to add some complexity

# Idea is that actions are glued to a configuration but can be applied independently of the configuration
# this allows for inheritance etc.
# '''


class ActionInterface(ABC):
    """
    Generic interface defining an abstract action
    """

    def __init__(self, configuration: ConfigurationWrapper):
        self._configuration = configuration

    @abstractmethod
    def action(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs) -> Any:
        try:
            return self.action(*args, **kwargs)
        except Exception as e:
            raise CiderBadActionException(e)
