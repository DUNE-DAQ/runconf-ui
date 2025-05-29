from runconf_ui.daq_config_interfaces.daq_config_file_io.daq_config_wrapper import DaqConfigurationWrapper
from runconf_ui.exceptions import CiderBadActionException

from abc import ABC, abstractmethod
from typing import Any
import logging
import traceback

# The idea here is to define an interface for actions on a configuration,
# currently this is very simple but there is scope to add some complexity

# Idea is that actions are glued to a configuration but can be applied independently of the configuration
# this allows for inheritance etc.
# '''

class ActionInterface(ABC):
    """
    Generic interface defining an abstract action
    """

    def __init__(self, configuration: DaqConfigurationWrapper):
        self._daq_configuration = configuration

    @abstractmethod
    def action(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs) -> Any:
        try:
            a = self.action(*args, **kwargs)
            return a
        except Exception:
            raise CiderBadActionException(traceback.format_exc())

    def __str__(self):
        return f"{self.__class__.__name__} using {self._daq_configuration.file_name}"