from runconf_ui.exceptions import CiderBadActionException
import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.utils.subsystem_status import SubsystemStatus
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)

from typing import Any, Optional, Dict
from abc import ABC, abstractmethod
import logging
import traceback


"""
Base classes for extracting the state of a subsystem. 

 Logic
    1. Input dict defined as

        System A:
            top_level_segement: str
            
            attributes:
              - id: strid: str
                class: str
                enabled_state: Any
                disabled_state: Any
                
                # If we want an additional button
                separate_system: bool
                label: str
              - ... 

            components:
              - id: str
                class: str
                enabled_state: bool
                disabled_state: bool
                
                # If we want an additional button
                separate_system: bool
                label: str
                - ...
    
        System B:
            ...
        
    2. Work out the state of each subsystem
        
"""


class ItemExtractor(ABC):
    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        disabled_dals=[],
    ):
        """
        Extracts the state of a subsystem. This is a base class for all extractors.


        :param daq_configuration: daq_configuration object
        :type daq_configuration: DaqConfigurationWrapper | None
        :param session_name: Name of session, defaults to None
        :type session_name: Optional[str], optional
        :param disabled_dals: List of disabled dals in daq_configuration, defaults to []
        :type disabled_dals: list, optional
        """

        # DAQ daq_configuration we're using
        self._application_controller = application_controller

        # The dal objects that are disabled
        self._disabled_dals = disabled_dals
        if (
            self._application_controller.buffer_daq_config is None
            or self._application_controller.session_name is None
        ):
            return

    def get_state(self, *args, **kwargs) -> SubsystemStatus:
        """
        Wrapper around the get state function. This is used to catch exceptions
        """
        try:
            return self._get_state(*args, **kwargs)
        except CiderBadActionException:
            return SubsystemStatus.STATE_NOT_DEFINED
        except Exception as e:
            logging.error(f"{traceback.format_exc()}")
            logging.error(f"Could not get state due to {e}")
            raise e

    @abstractmethod
    def _get_state(self, *args, **kwargs) -> SubsystemStatus:
        # Abstract method, use for getting state
        pass

    @abstractmethod
    def _set_state(self, state: SubsystemStatus, *args, **kwargs):
        # Abstract method, use for setting state
        pass

    def set_state(self, state: SubsystemStatus, *args, **kwargs):
        """
        Wrapper around the set state function. This is used to catch exceptions
        """
        try:
            self._set_state(state, *args, **kwargs)
        except CiderBadActionException:
            logging.debug("Could not set state")
            logging.debug(f"{traceback.format_exc()}")
        except Exception as e:
            logging.error(f"{traceback.format_exc()}")
            logging.error(f"Could not set state due to {e}")
            raise e

    def get_disabled_dals(self):
        return self._disabled_dals

    def set_disabled_dals(self, disabled_dals):
        self._disabled_dals = disabled_dals


class SubsystemExtractor(ItemExtractor):
    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        subsystem: dict,
        disabled_dals=[],
    ):
        """
        Base class for extracting the state of a single subsystem.

        :param daq_configuration: daq_configuration object
        :type daq_configuration: DaqConfigurationWrapper | None
        :param session_name: Name of session
        :type session_name: str
        :param subsystem: Dictionary containing subsystem information
        :type subsystem: dict
        :param disabled_dals: List of disabled dals, defaults to []
        :type disabled_dals: list, optional


        Here subsystem dict is of the following form:
        {
            "id": str,                 # name of subsystem
            "class": str,              # DAL object class [i.e. "Segment", "Attribute"]
            "enabled_state": Any,      # enabled state of subsystem
            "disabled_state": Any,     # disabled state of subsystem
            'separate_system": bool,   # Does this require an additional button to the full system?
            "system_label": str,       # If it's a separate system, what is its name?
        }


        """

        super().__init__(application_controller, disabled_dals)

        # Subsystem information
        self._subsystem = subsystem
        self._session_dal = ca.GetDalObjectAction(
            self._application_controller.buffer_daq_config
        )(self._application_controller.session_name, "Session")

        # Attributes

        # DAL object class
        self._system_class = subsystem["class"]
        # DAL object id
        self._system_id = subsystem["id"]

        # Enabled and disabled states i.e. what does it mean to be enabled/disabled
        self._enabled_state = subsystem.get("enabled_state", True)
        self._disabled_state = subsystem.get("disabled_state", False)

        # If this is a sub-system of the full system object, we need to know if it has a separate button
        self._is_system = subsystem.get("separate_system", False)
        # If it is a seoarate system, we need to know what the system name is
        self._system_name = subsystem.get("system_label", None)

        if self._is_system and self._system_name is None:
            raise CiderBadActionException(
                f"Subsystem {self._system_id} is a system but does not have a system name"
            )

        self._tooltip = ""
        if self._is_system:
            self._tooltip = subsystem.get(
                "tooltip", f"Enable/disable {self._system_name} subsystem"
            )

    @property
    def tooltip(self) -> Optional[str]:
        return self._tooltip

    @tooltip.setter
    def tooltip(self, tooltip: Optional[str]):
        self._tooltip = tooltip

    @property
    def is_system(self) -> bool:
        return self._is_system

    @is_system.setter
    def is_system(self, is_system: bool):
        self._is_system = is_system

    @property
    def system_name(self) -> str:
        return self._system_name

    @system_name.setter
    def system_name(self, name: str):
        self._system_name = name

    @property
    def system_id(self) -> str:
        return self._system_id

    @property
    def system_class(self) -> str:
        return self._system_class

    @property
    def enabled_state(self) -> Any:
        return self._enabled_state

    @enabled_state.setter
    def enabled_state(self, state: Any):
        self._enabled_state = state

    @property
    def disabled_state(self) -> Any:
        return self._disabled_state

    @disabled_state.setter
    def disabled_state(self, state: Any):
        self._disabled_state = state


class MultiItemExtractor(ItemExtractor):
    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        system: Dict | None = None,
        disabled_dals=[],
    ):
        """
        :param daq_configuration: daq_configuration object
        :param session_name: Name of session, defaults to None
        :param system: Dictionary containing system information, defaults to None
        :param disabled_dals: List of disabled dals, defaults to []

        Base class for extracting the state of multiple items. This is used to extract the state of a full subsystem
        """
        super().__init__(application_controller, disabled_dals)

        if (
            self._application_controller.buffer_daq_config is not None
            and system is not None
        ):
            self.read_system(system)

    def read_system(self, system: Optional[Dict]):
        if (
            system is None
            or self._application_controller.buffer_daq_config is None
            or self._application_controller.session_name is None
        ):
            return False

        return True

