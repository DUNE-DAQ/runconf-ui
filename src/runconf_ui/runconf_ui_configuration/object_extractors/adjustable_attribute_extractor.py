from runconf_ui.runconf_ui_controllers.runconf_ui_state import ShifterInterfaceState
import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.exceptions import CiderOutOfBoundsException

import logging


class AdjustableAttributeManager:
    def __init__(self, application_controller: ShifterInterfaceState, **kwargs):
        self._application_controller = application_controller

        self._upper_limit = kwargs.get("upper_limit", None)
        self._lower_limit = kwargs.get("lower_limit", None)
        self._convert_to_period = kwargs.get("convert_to_tick", False)

        self._object_list = []
        self._object_ids = []
        self._init_values = {}

        object_id = kwargs.get("object_id", None)
        self._object_class = kwargs.get("object_class", None)

        self._attribute_name = kwargs.get("attribute_name", None)

        if not self._attribute_name:
            raise ValueError("Attribute name must be provided.")

        if (
            self._application_controller.buffer_daq_config is None
            or self._application_controller.session_name is None
        ):
            return

        self._CLOCK_RATE = 62.5e6  # Clock rate in Hz

        if not self._object_class:
            raise ValueError("Attribute class must be provided.")

        # Means we can use the attribute class to get the object list
        if object_id is None or "":
            self._object_list = ca.GetDalsOfClassAction(
                self._application_controller.buffer_daq_config
            )(self._object_class)
        else:
            self._object_list = [
                ca.GetDalObjectAction(self._application_controller.buffer_daq_config)(
                    object_id, self._object_class
                )
            ]

        # Get the object IDs for the objects in the list and store
        self._object_ids = [
            ca.GetAttributeAction(self._application_controller.buffer_daq_config)(
                obj, "id"
            )
            for obj in self._object_list
        ]

        # Store initial values for the attribute
        self._init_values = {
            ca.GetAttributeAction(self._application_controller.buffer_daq_config)(
                obj, "id"
            ): ca.GetAttributeAction(self._application_controller.buffer_daq_config)(
                obj, self._attribute_name
            )
            for obj in self._object_list
        }

    def convert_to_period(self, value: float) -> float:
        """
        Convert the value to a period if required.
        """
        n_ticks = round(self._CLOCK_RATE / value)
        return n_ticks

    def convert_to_hertz(self, value: int) -> float:
        """
        Convert the value from a period to hertz if required.
        """
        return self._CLOCK_RATE / value

    def set_state(self, object_id: str, value: float) -> None:
        """
        Set the attribute value for all objects in the object list.
        If convert_to_period is True, convert the value to a period before setting.
        """
        if self._upper_limit is not None and value > self._upper_limit:
            raise CiderOutOfBoundsException(
                f"Value {value} exceeds upper limit {self._upper_limit}."
            )

        if self._lower_limit is not None and value < self._lower_limit:
            raise CiderOutOfBoundsException(
                f"Value {value} is below lower limit {self._lower_limit}."
            )

        if object_id not in self._object_ids:
            logging.debug(f"Object ID {object_id} not found in object list.")
            raise ValueError(f"Object ID {object_id} not found in object list.")

        if self._convert_to_period:
            value = self.convert_to_period(value)

        for obj in self._object_list:
            if (
                not ca.GetAttributeAction(
                    self._application_controller.buffer_daq_config
                )(obj, "id")
                == object_id
            ):
                continue

            ca.ChangeAttributeAction(self._application_controller.buffer_daq_config)(
                obj, self._attribute_name, value
            )

            ca.UpdateDalAction(self._application_controller.buffer_daq_config)(obj)

    def get_state(self, object_id: str) -> float:
        for obj in self._object_list:
            if (
                ca.GetAttributeAction(self._application_controller.buffer_daq_config)(
                    obj, "id"
                )
                == object_id
            ):

                attr_value = ca.GetAttributeAction(
                    self._application_controller.buffer_daq_config
                )(obj, self._attribute_name)

                if self._convert_to_period:
                    return self.convert_to_hertz(attr_value)

                return ca.GetAttributeAction(
                    self._application_controller.buffer_daq_config
                )(obj, self._attribute_name)

    def get_object_list(self) -> list[str]:
        """
        Get the list of object IDs for which the attribute can be set.
        """
        return self._object_ids

    def get_all_states(self) -> dict:
        return {
            obj: {"state": self.get_state(obj), "attribute": self._attribute_name}
            for obj in self._object_ids
        }

    def get_tooltip(self, object_id: str) -> str:
        if object_id not in self._object_ids:
            logging.debug(f"Object ID {object_id} not found in object list.")
            return "Object ID not found."

        object = ca.GetDalObjectAction(self._application_controller.buffer_daq_config)(
            object_id, self._object_class
        )

        attribute_value = ca.GetAttributeAction(
            self._application_controller.buffer_daq_config
        )(object, self._attribute_name)

        if isinstance(attribute_value, float):
            f"{attribute_value:3f} Hz"

        tooltip = f"{attribute_value} Hz"

        if self._lower_limit is not None and self._upper_limit is not None:
            tooltip += f"\nLimits: [{self._lower_limit:3f}, {self._upper_limit}] Hz"
        elif self._lower_limit is not None:
            tooltip += f"\nLower Limit: {self._lower_limit:3f} Hz"
        elif self._upper_limit is not None:
            tooltip += f"\nUpper Limit: {self._upper_limit:3f} Hz"

        return tooltip

    def get_init_values(self):
        if not self._object_ids:
            return {}

        return {obj_id: self._init_values[obj_id] for obj_id in self._object_ids}

    def reset_value(self, object_id: str) -> None:
        """
        Reset the attribute value for the given object ID to its initial value.
        """
        if object_id not in self._object_ids:
            logging.debug(f"Object ID {object_id} not found in object list.")
            raise ValueError(f"Object ID {object_id} not found in object list.")

        init_value = self._init_values[object_id]

        if self._convert_to_period:
            init_value = self.convert_to_period(init_value)

        self.set_state(object_id, init_value)

    @property
    def upper_limit(self) -> float | None:
        return self._upper_limit

    @property
    def lower_limit(self) -> float | None:
        return self._lower_limit

    @property
    def attribute_name(self) -> str:
        return self._attribute_name
