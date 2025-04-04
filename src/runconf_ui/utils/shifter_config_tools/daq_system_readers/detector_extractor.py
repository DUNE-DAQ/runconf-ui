from runconf_ui.interfaces.controller.daq_conf_wrapper import DaqConfigurationWrapper
from runconf_ui.utils.shifter_config_tools.daq_system_readers.extractor_interfaces import MultiItemExtractor, SubsystemStatus
from runconf_ui.utils.shifter_config_tools.daq_system_readers.system_extractor import SystemExtractor
from runconf_ui.exceptions import CiderBadActionException
from runconf_ui.utils.subsystem_status import SubsystemStatus

from typing import Dict, Optional
import logging
import traceback


class DetectorExtractor(MultiItemExtractor):
    def __init__(
        self,
        daq_configuration: DaqConfigurationWrapper,
        session: str | None,
        detector_config: Optional[Dict],
        disabled_dals=[],
    ):
        '''
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
        
        '''
        # Config file
        self._detector_config = {}
        # List of systems in the detector config
        self._system_extractors = []
        super().__init__(daq_configuration, session, detector_config, disabled_dals)

    def read_system(self, detector_config: Dict):
        # Read system dict
        if not super().read_system(detector_config):
            return

        self._detector_config = detector_config
        self._system_extractors = []

        extracted_systems = detector_config.get("Systems", [])
        system_name = list(detector_config.keys())[0]
        
        logging.debug(f"Reading system {system_name}")

        for s in extracted_systems:
            try:
                system_name = list(s.keys())[0]

                system_info = list(s.values())[0]

                self._system_extractors.append(
                    SystemExtractor(
                        self._daq_configuration,
                        self._session_name,
                        system_name,
                        system_info,
                    )
                )
            except CiderBadActionException:
                logging.debug(f"Could not extract system {system_name}")
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
                return_dict.update(system.get_all_states())
            except CiderBadActionException:
                logging.debug(f"Could not get all states for {system.system_name}")
                logging.debug(f"{traceback.format_exc()}")
            except Exception as e:
                logging.error(f"{traceback.format_exc()}")
                logging.error(
                    f"Could not get all states for {system.system_name} due to {e}"
                )
                raise e

        logging.debug(f"All states: {return_dict}")
        return return_dict

    @property
    def system_info(self):
        return self._detector_config
