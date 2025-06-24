from runconf_ui.runconf_ui_controllers.runconf_ui_state import ShifterInterfaceState
import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.exceptions import CiderOutOfBoundsException

import logging
from typing import Tuple, Union

class AdjustableAttributeManager:
    def __init__(self, application_controller: ShifterInterfaceState, **kwargs):
        '''
        Initialize the AdjustableAttributeManager with the application controller and configuration options.
        :param application_controller: The application controller managing the DAQ configuration.

        :param kwargs: Additional configuration options such as upper_limit, lower_limit, convert_to_tick, object_id, object_class, and attribute_name.        
        
        '''
        self._application_controller = application_controller

        self._upper_limit = kwargs.get("upper_limit", None)
        self._lower_limit = kwargs.get("lower_limit", None)

        self._database_hex = kwargs.get("hex_database", False)
        self._convert_to_period = kwargs.get("convert_to_tick", False)
        self._unit_scale = kwargs.get("unit_scale", 1.0)  # Default scale factor for conversion
        self._unit_label = kwargs.get("unit_label", "Hz")

        # Get the range of the attribute if specified in the configuration
        self._lower_limit, self._upper_limit = self._range()

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


    def set_state(self, object_id: str, value) -> None:
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

        value = value * self._unit_scale

        # Convert value to hexadecimal if required
        if self._database_hex:
            value = self.to_hex(value)

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

    def get_state(self, object_id: str) :
        '''
        Get state of the attribute for a given object ID.
        :param object_id: The ID of the object to get the state for.
        :return: The value of the attribute for the object, converted to hertz if required.
        '''
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



                attr_value *= self._unit_scale
                if self._database_hex:
                    attr_value = self.to_dec(attr_value)
                
                return attr_value
                

    def get_object_list(self) -> list[str]:
        """
        Get the list of object IDs for which the attribute can be set.
        """
        return self._object_ids

    def get_all_states(self) -> dict:
        '''
        Get state of the attribute for all objects in the object list.
        '''
        return {
            obj: {"state": self.get_state(obj), "attribute": self._attribute_name}
            for obj in self._object_ids
        }

    def get_tooltip(self, object_id: str) -> str:
        '''
        Get the tooltip for the attribute value of a given object ID.
        '''
        if object_id not in self._object_ids:
            logging.debug(f"Object ID {object_id} not found in object list.")
            return "Object ID not found."

        object = ca.GetDalObjectAction(self._application_controller.buffer_daq_config)(
            object_id, self._object_class
        )

        attribute_value = ca.GetAttributeAction(
            self._application_controller.buffer_daq_config
        )(object, self._attribute_name)

        if self._convert_to_period:
            attribute_value = self.convert_to_hertz(attribute_value)
        tooltip = f"{attribute_value:3f} {self._unit_label}"

        if self._lower_limit is not None and self._upper_limit is not None:
            tooltip += f"\nLimits: [{self._lower_limit:3f}, {self._upper_limit}] {self._unit_label}"
        elif self._lower_limit is not None:
            tooltip += f"\nLower Limit: {self._lower_limit:3f} {self._unit_label}"
        elif self._upper_limit is not None:
            tooltip += f"\nUpper Limit: {self._upper_limit:3f} {self._unit_label}"

        return tooltip

    def get_init_values(self):
        if not self._object_ids:
            return {}
        return {obj_id: self._init_values[obj_id] for obj_id in self._object_ids}

    def to_hex(self, value: float) -> str:
        return hex(int(value))
    
    def to_dec(self, value: str) -> int:
        return int(value, 16)

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


    def _range(self)->Union[Tuple[float, float], Tuple[None, None]]:
        """
        Get the range of the attribute.
        Returns a tuple of (lower_limit, upper_limit).
        If limits are not set, returns (None, None).
        """
        range_str = ca.GetConfigAttributePropertiesAction(
            self._application_controller.buffer_daq_config
        )(self._object_class, self._attribute_name, "range")
        
        if range_str is None or range_str == "None":
            return None, None
        
        upper, lower = range_str.split("..")
        
        return float(lower), float(upper)