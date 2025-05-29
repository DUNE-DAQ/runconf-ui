from runconf_ui.daq_config_interfaces.actions.workflows.get_set_session_attribute import (
    SetAttributeValueSessionAction,
    GetAttributeValueSessionAction,
)
from runconf_ui.daq_config_interfaces.daq_config_file_io.daq_config_wrapper import DaqConfigurationWrapper
from runconf_ui.runconf_ui_configuration.detector_config_readers.extractor_interfaces import SubsystemExtractor
import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.daq_config_interfaces.actions.workflows.get_objects_in_session import (
    GetSegmentAppsListAction,
)
from runconf_ui.exceptions import CiderBadActionException
from runconf_ui.utils.subsystem_status import SubsystemStatus
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)


from typing import Dict
import logging
import traceback

class AttributeExtractor(SubsystemExtractor):
    '''
    Class for extracting the state of an attribute within a subsystem
    '''
    
    def __init__(
        self, 
        application_controller: ShifterInterfaceState,
        subsystem: Dict,
        disabled_dals=[],
    ):

        super().__init__(application_controller, subsystem, disabled_dals)

        self._segments = subsystem.get("segments", ["root-segment"])
        segment_dals = []

        for s in self._segments:
            try:
                segment_dals.append(
                    ca.GetDalObjectAction(self._application_controller.buffer_daq_config)(s, "Segment")
                )
            except CiderBadActionException:
                logging.debug(
                    f"Could not get segment {s} for subsystem {self._system_id}"
                )
            except Exception as e:
                logging.error(f"{traceback.format_exc()}")
                logging.error(
                    f"Could not get segment {s} for subsystem {self._system_id} due to {e}"
                )
                raise e

        self._affected_objects = list(
            set(
                ca.GetAttributeAction(self._application_controller.buffer_daq_config)(a, "id")
                for t in segment_dals
                for a in GetSegmentAppsListAction(self._application_controller.buffer_daq_config)(t)
                if ca.GetClassNameAction(self._application_controller.buffer_daq_config)(a) == subsystem["class"]
            )
        )

    def _get_state(self) -> SubsystemStatus | None:
        current_states = GetAttributeValueSessionAction(self._application_controller.buffer_daq_config)(
            self._session_dal,
            self._system_class,
            self._system_id,
            self._affected_objects,
        )

        if len(current_states) == 0:
            return SubsystemStatus.STATE_NOT_DEFINED

        state = current_states[0]

        if all(
            [
                self.get_state_for_obj(a) == SubsystemStatus.DISABLED
                for a in self._affected_objects
            ]
        ):
            return SubsystemStatus.DISABLED

        for s in current_states:
            if s != state:
                return SubsystemStatus.PARTIALLY_ENABLED

        return (
            SubsystemStatus.ENABLED
            if s == self._enabled_state
            else SubsystemStatus.DISABLED
        )

    def get_state_for_obj(self, object_name: str) -> SubsystemStatus:
        try:
            object_dal = ca.GetDalObjectAction(self._application_controller.buffer_daq_config)(
                object_name, self._system_class
            )
            object_state = (
                ca.GetAttributeAction(self._application_controller.buffer_daq_config)(object_dal, self._system_id)
            )

            if object_state == self._disabled_dals or object_dal in self._disabled_dals:
                return SubsystemStatus.DISABLED
            else:

                return SubsystemStatus.ENABLED
            

        except Exception:
            raise CiderBadActionException(
                f"Could not get state for object {object_name} in subsystem {self._system_id}"
            )

    def _set_state(self, state: SubsystemStatus):
        if state == SubsystemStatus.PARTIALLY_ENABLED:
            raise CiderBadActionException(
                "Cannot set partially enabled state for an attribute"
            )

        state_value = (
            self._enabled_state
            if state == SubsystemStatus.ENABLED
            else self._disabled_state
        )
        
        print(f"Setting state for {self._system_id} to {state_value}")

        SetAttributeValueSessionAction(self._application_controller.buffer_daq_config).action(
            self._session_dal,
            self._system_class,
            self._system_id,
            state_value,
            self._affected_objects,
        )

    def get_affected_object_names(self):
        if self._affected_objects is None:
            return []

        return self._affected_objects

    def get_affected_object(self, obj_name):
        if obj_name in self._affected_objects:
            return ca.GetDalObjectAction(self._application_controller.buffer_daq_config)(
                obj_name, self._system_class
            )
        return None

    def get_affected_object_dals(self):
        return [
            ca.GetDalObjectAction(self._application_controller.buffer_daq_config)(a, self._system_class)
            for a in self._affected_objects
        ]
