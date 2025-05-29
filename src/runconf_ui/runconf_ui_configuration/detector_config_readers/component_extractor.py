from runconf_ui.runconf_ui_configuration.detector_config_readers.extractor_interfaces import (
    SubsystemExtractor,
)
import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.exceptions import CiderBadActionException
from runconf_ui.utils.subsystem_status import SubsystemStatus

import logging


class ComponentExtractor(SubsystemExtractor):
    """
    Extracts the state of a single COMPONENT based subsystem. For example CRP enabled/disabled

    System info dict of the form

    id: str,                 # name of component
    class: str,              # DAL object class with this component [i.e. "Segment", "Attribute"]
    enabled_state: Any,      # enabled state of subsystem
    disabled_state: Any,     # disabled state of subsystem
    separate_system: bool,   # Does this require an additional button to the full system?
    system_label: str,      # If it's a separate system, what is its name?

    """

    def _get_state(self) -> SubsystemStatus:
        """
        Get state of the subsystem. This is always a boolean true/false
        """

        subsystem_dal = self.get_dal()

        dal_disabled = ca.CheckIsDisabledAction(
            self._application_controller.buffer_daq_config
        )(subsystem_dal, self._application_controller.session_name)

        return SubsystemStatus(
            not dal_disabled and subsystem_dal not in self._disabled_dals
        )

    def _set_state(self, state: SubsystemStatus):
        if state == SubsystemStatus.PARTIALLY_ENABLED:
            raise CiderBadActionException(
                "Cannot set partially enabled state for a component"
            )

        subsystem_dal = ca.GetDalObjectAction(
            self._application_controller.buffer_daq_config
        )(self._system_id, self._system_class)

        # Disable dal
        ca.DisableDalAction(self._application_controller.buffer_daq_config)(
            subsystem_dal, self._application_controller.session_name, not state
        )

        # Update OKS object for dal and session
        ca.UpdateDalAction(self._application_controller.buffer_daq_config)(
            subsystem_dal
        )
        ca.UpdateDalAction(self._application_controller.buffer_daq_config)(
            self._session_dal
        )

        logging.debug(
            f"Subsystem {self._system_id} is {'disabled' if not state else 'enabled'}"
        )

    def get_dal(self):
        return ca.GetDalObjectAction(self._application_controller.buffer_daq_config)(
            self._system_id, self._system_class
        )

    def is_filtered(self) -> bool:
        subsystem_filters = self._subsystem.get("filters", [])

        for filter in subsystem_filters:
            attribute = filter.get("attribute")
            values = filter.get("value", [])

            try:
                for value in values:
                    if (
                        ca.GetAttributeAction(
                            self._application_controller.buffer_daq_config
                        )(self.get_dal(), attribute)
                        == value
                    ):
                        return True

            except CiderBadActionException:
                # If the attribute does not exist, we ignore it
                logging.warning(
                    f"Bad filter: Attribute {attribute} not found in DAL object {self.get_dal()} when trying to apply filter."
                )

        return False

    @property
    def tooltip(self) -> str:

        # We can try to get the attribute
        try:
            return ca.GetAttributeAction(
                self._application_controller.buffer_daq_config
            )(self.get_dal(), self._tooltip)
        except CiderBadActionException:
            logging.debug("Tooltip attribute not found, using default tooltip.")

        if self._is_system:
            return f"Enable/disable {self._system_name} component"
        else:
            return f"Enable/disable {self._system_id} component"
