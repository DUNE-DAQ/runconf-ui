from runconf_ui.runconf_ui_configuration.object_extractors.extractor_interfaces import (
    MultiItemExtractor,
)
from runconf_ui.runconf_ui_configuration.object_extractors.system_extractor import (
    SystemExtractor,
)
from runconf_ui.exceptions import (
    CiderBadActionException,
    CiderInvalidConfigurationException,
)
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)

from runconf_ui.utils.subsystem_status import SubsystemStatus

from typing import Dict, Optional
import logging
import traceback
from collections import OrderedDict
import re


class DetectorExtractor(MultiItemExtractor):
    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        detector_config: Optional[Dict],
        disabled_dals=[],
    ):
        """
        Extracts the states of ALL systems present in the detector config for a given top level system (i.e. trigger).
        :param daq_configuration: daq_configuration object
        :param session: Name of session
        :param detector_config: Dictionary containing detector information
        :param disabled_dals: List of disabled dals, defaults to []

        Detector config is of the form

        "Detector System Name": {
            - label: str     # Name of the system for labelling widgets
            - panel_type:    # multi-system OR single system
            - Systems [
                {systsem_a},
                {system_b},
                ...
            ]
        }

        """
        # Config file
        self._detector_config = {}
        # List of systems in the detector config
        self._system_extractors = []
        logging.debug("Initializing DetectorExtractor...")
        logging.debug(f"Detector configuration {detector_config}")
        super().__init__(application_controller, detector_config, disabled_dals)

    def read_system(self, detector_config: Dict):
        # Read system dict
        if not super().read_system(detector_config):
            logging.error("Detector config is not valid, cannot read systems.")
            logging.error(f"Detector config: {detector_config}")
            return

        self._detector_config = detector_config
        self._system_extractors = []
        logging.debug(f"Detector config: {self._detector_config}")

        extracted_systems = detector_config.get("Systems", [])
        system_name = list(detector_config.keys())[0]

        logging.debug(f"Reading system {system_name}")

        for s in extracted_systems:
            logging.debug(f"Extracting system {s}")
            try:
                system_name = list(s.keys())[0]

                system_info = list(s.values())[0]

                self._system_extractors.append(
                    SystemExtractor(
                        self._application_controller,
                        system_name,
                        system_info,
                    )
                )
            except CiderBadActionException:
                logging.debug(f"Could not extract system {system_name}")
                logging.debug(f"{traceback.format_exc()}")
            except Exception as e:
                logging.error(f"Could not extract system {system_name} due to {e}")
                logging.error(f"{traceback.format_exc()}")
                raise e

    def _set_state(self, state: SubsystemStatus, state_name: str):
        # Set state for a system in the detector config
        if state == SubsystemStatus.STATE_NOT_DEFINED:
            # Can't handle this
            return

        # Find correct system
        for system in self._system_extractors:
            # Check given system extractor contains the system name
            if state_name not in system.system_names:
                continue

            if state_name == system.system_name:
                for s in system.system_names:
                    system.set_state(state, s)
            else:
                system.set_state(state, state_name)

    def _get_state(self, state_name: str):
        for system in self._system_extractors:
            if state_name in system.system_names:
                return system.get_state(state_name)

        return SubsystemStatus.STATE_NOT_DEFINED

    @property
    def systems(self):
        return self._system_extractors

    def set_disabled_dals(self, disabled_dals):
        super().set_disabled_dals(disabled_dals)
        for system in self._system_extractors:
            system.set_disabled_dals(disabled_dals)

    def get_all_states(self):
        return_dict = {}
        # grab big dict
        for system in self._system_extractors:
            try:
                system_dict = system.get_all_states()

                main_syst = system_dict.pop(
                    system.system_name, None
                )  # Remove system name key
                if main_syst is not None:
                    return_dict[system.system_name] = (
                        main_syst  # Add it back as the first item
                    )

                # Sort by value
                ordered_states = OrderedDict(
                    sorted(
                        sorted(system_dict.items(), key=self.__natural_sort_key),
                        key=lambda item: item[1] != SubsystemStatus.ENABLED,
                    )
                )

                return_dict.update(ordered_states)

            except CiderBadActionException:
                logging.debug(f"Could not get all states for {system.system_name}")
                logging.debug(f"{traceback.format_exc()}")
            except Exception as e:
                logging.error(f"{traceback.format_exc()}")
                logging.error(
                    f"Could not get all states for {system.system_name} due to {e}"
                )
                raise CiderInvalidConfigurationException(e)

        logging.debug(f"All states: {return_dict}")
        return return_dict

    @property
    def system_info(self):
        return self._detector_config

    def get_tooltip(self, state_name: str) -> str:
        for system in self._system_extractors:
            if state_name in system.system_names:
                return system.get_tooltip(state_name)

        return "No tooltip available for this state"

    # Natural sort key function, lets us display things like HLT In a "nice" ordering
    def __natural_sort_key(self, s):
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split("([0-9]+)", s[0])
        ]

    def get_is_subsystem(self, state_name: str) -> bool:
        """
        Check if the state name corresponds to a subsystem.

        Args:
            state_name: The name of the state to check.

        Returns:
            True if the state name corresponds to a subsystem, False otherwise.
        """
        for system in self._system_extractors:
            # If it's the full system name, it's not a subsystem
            if state_name == system.system_name:
                return False

        return True
