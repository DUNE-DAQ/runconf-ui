from runconf_ui.runconf_ui_configuration.detector_config_readers.extractor_interfaces import SubsystemExtractor
import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.exceptions import CiderBadActionException
from runconf_ui.utils.subsystem_status import SubsystemStatus

import logging


class ComponentExtractor(SubsystemExtractor):
    '''
    Extracts the state of a single COMPONENT based subsystem. For example CRP enabled/disabled
    
    System info dict of the form
    
    id: str,                 # name of component
    class: str,              # DAL object class with this component [i.e. "Segment", "Attribute"]
    enabled_state: Any,      # enabled state of subsystem
    disabled_state: Any,     # disabled state of subsystem
    separate_system: bool,   # Does this require an additional button to the full system?
    system_label: str,      # If it's a separate system, what is its name?
    
    '''
    def _get_state(self) -> SubsystemStatus:
        '''
        Get state of the subsystem. This is always a boolean true/false
        '''
        
        subsystem_dal = self.get_dal()

        dal_disabled = ca.CheckIsDisabledAction(self._daq_configuration)(
            subsystem_dal, self._session_name
        )

        logging.debug(
            f"Subsystem {self._system_id} is {'disabled' if dal_disabled else 'enabled'}"
        )

        return SubsystemStatus(
            not dal_disabled and subsystem_dal not in self._disabled_dals
        )

    def _set_state(self, state: SubsystemStatus):
        if state == SubsystemStatus.PARTIALLY_ENABLED:
            raise CiderBadActionException(
                "Cannot set partially enabled state for a component"
            )

        subsystem_dal = ca.GetDalObjectAction(self._daq_configuration)(
            self._system_id, self._system_class
        )

        # Disable dal
        ca.DisableDalAction(self._daq_configuration)(
            subsystem_dal, self._session_name, not state
        )
    
        # Update OKS object for dal and session
        ca.UpdateDalAction(self._daq_configuration)(subsystem_dal)
        ca.UpdateDalAction(self._daq_configuration)(self._session_dal)
        
        logging.debug(
            f"Subsystem {self._system_id} is {'disabled' if not state else 'enabled'}")

    def get_dal(self):
        return ca.GetDalObjectAction(self._daq_configuration)(
            self._system_id, self._system_class
        )

