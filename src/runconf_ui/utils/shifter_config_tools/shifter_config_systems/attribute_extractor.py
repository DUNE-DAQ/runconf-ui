from runconf_ui.interfaces.workflows.get_set_session_attribute import (
    SetAttributeValueSessionAction,
    GetAttributeValueSessionAction,
)
from runconf_ui.interfaces.controller.daq_conf_wrapper import DaqConfigurationWrapper
from runconf_ui.utils.shifter_config_tools.shifter_config_systems.extractor_interfaces import SubsystemExtractor
import runconf_ui.interfaces.actions.actions as ca
from runconf_ui.interfaces.workflows.get_objects_in_session import (
    GetSegmentAppsListAction,
)
from runconf_ui.exceptions import CiderBadActionException
from runconf_ui.utils.subsystem_status import SubsystemStatus


from typing import Dict
import logging
import traceback

class AttributeExtractor(SubsystemExtractor):
    '''
    Class for extracting the state of an attribute within a subsystem
    '''
    
    def __init__(
        self,
        daq_configuration: DaqConfigurationWrapper | None,
        session_name: str,
        subsystem: Dict,
        disabled_dals=[],
    ):

        super().__init__(daq_configuration, session_name, subsystem, disabled_dals)

        self._segments = subsystem.get("segments", ["root-segment"])
        segment_dals = []

        for s in self._segments:
            try:
                segment_dals.append(
                    ca.GetDalObjectAction(self._daq_configuration)(s, "Segment")
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
                ca.GetAttributeAction(self._daq_configuration)(a, "id")
                for t in segment_dals
                for a in GetSegmentAppsListAction(self._daq_configuration)(t)
                if ca.GetClassNameAction(self._daq_configuration)(a) == subsystem["class"]
            )
        )

    def _get_state(self) -> SubsystemStatus | None:
        current_states = GetAttributeValueSessionAction(self._daq_configuration)(
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
            object_dal = ca.GetDalObjectAction(self._daq_configuration)(
                object_name, self._system_class
            )
            object_state = (
                ca.GetAttributeAction(self._daq_configuration)(object_dal, self._system_id)
                and object_dal not in self._disabled_dals
            )

            if object_state == self._enabled_state:
                logging.debug(
                    f"Object {object_name} in subsystem {self._system_id} is enabled")
                return SubsystemStatus.ENABLED
            else:
                logging.debug(
                    f"Object {object_name} in subsystem {self._system_id} is disabled"
                )
                return SubsystemStatus.DISABLED
            

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

        SetAttributeValueSessionAction(self._daq_configuration).action(
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
            return ca.GetDalObjectAction(self._daq_configuration)(
                obj_name, self._system_class
            )
        return None

    def get_affected_object_dals(self):
        return [
            ca.GetDalObjectAction(self._daq_configuration)(a, self._system_class)
            for a in self._affected_objects
        ]
