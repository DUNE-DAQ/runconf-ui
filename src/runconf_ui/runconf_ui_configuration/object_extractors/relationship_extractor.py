import logging

import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.daq_config_interfaces.daq_config_file_io.daq_config_wrapper import (
    DaqConfigurationWrapper,
)
from runconf_ui.runconf_ui_configuration.object_extractors.attribute_extractor import (
    AttributeExtractor,
)
from runconf_ui.runconf_ui_controllers.runconf_ui_state import ShifterInterfaceState


class RelationshipExtractor(AttributeExtractor):
    """
    Extracts the state of a relationship within a subsystem.

    This class extends the AttributeExtractor to handle relationships specifically.
    """

    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        subsystem: dict,
        disabled_dals: list[str] = None,
    ):
        """
        Initialize the RelationshipExtractor.

        Args:
            application_controller: The shifter interface state controller
            subsystem: Dictionary containing subsystem configuration
            disabled_dals: List of disabled DALs (default empty list)
        """
        if disabled_dals is None:
            disabled_dals = []
        super().__init__(application_controller, subsystem, disabled_dals)

        self._relationship_class = subsystem.get("relationship_class")
        # Initialize states
        self.enabled_state = self._find_enable_disable_state(self.enabled_state)
        self.disabled_state = self._find_enable_disable_state(self.disabled_state)

    def _get_states(
        self, state: str | list[str], configuration: DaqConfigurationWrapper
    ) -> object | list[object]:
        """
        Get DAL objects for the given state(s).

        Args:
            state: Either a single state name or list of state names
            configuration: The DAQ configuration to use

        Returns:
            Either a single DAL object or list of DAL objects
        """
        if not isinstance(state, list):
            return ca.GetDalObjectAction(configuration)(state, self._relationship_class)

        return [
            ca.GetDalObjectAction(configuration)(d, self._relationship_class)
            for d in state
        ]

    def _find_enable_disable_state(
        self, state: str | list[str]
    ) -> object | list[object] | None:
        """
        Get DALs to set relationship enable/disable state.

        Args:
            state: Either a single state name or list of state names

        Returns:
            The state object(s) or None if not found
        """
        try:
            # First try with buffer config
            return self._get_states(
                state, self._application_controller.buffer_daq_config
            )
        except Exception:
            logging.debug(
                "Couldn't find enable/disable state in buffer config, trying full config. "
            )

        try:
            # Fall back to full config
            full_config = DaqConfigurationWrapper(
                self._application_controller.current_daq_config
            )
            states = self._get_states(state, full_config)

            # Copy found states to buffer config
            states_list = [states] if not isinstance(states, list) else states
            for state_obj in states_list:
                copied_obj = ca.CopyDalAction(full_config)(state_obj)
                ca.UpdateDalAction(self._application_controller.buffer_daq_config)(
                    copied_obj
                )
                ca.CommitConfigurationAction(
                    self._application_controller.buffer_daq_config
                )()

            return self._get_states(
                state, self._application_controller.buffer_daq_config
            )

        except Exception as e:
            logging.error(f"Failed to find enable/disable state: {e!s}")
            return None