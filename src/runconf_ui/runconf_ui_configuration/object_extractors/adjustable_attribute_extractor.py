import logging
import re

import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.exceptions import CiderOutOfBoundsException
from runconf_ui.runconf_ui_controllers.runconf_ui_state import ShifterInterfaceState


class AdjustableAttributeManager:
    def __init__(self, application_controller: ShifterInterfaceState, **kwargs):
        """
        Initialize the AdjustableAttributeManager with the application controller and configuration options.
        :param application_controller: The application controller managing the DAQ configuration.

        :param kwargs: Additional configuration options such as upper_limit, lower_limit, object_id, object_class, and attribute_name.

        """
        self._application_controller = application_controller

        self._is_hex = kwargs.get(
            "is_hex", False
        )  # Whether to convert values to hexadecimal when saving

        self._unit_scale = kwargs.get(
            "unit_scale", 1.0
        )  # Default scale factor for conversion
        self._unit_label = kwargs.get("unit_label", "")  # Default unit label
        self._filter_by = kwargs.get("filters", None)

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
            unfliltered_list = ca.GetDalsOfClassAction(
                self._application_controller.buffer_daq_config
            )(self._object_class)
            self._object_list = [obj for obj in unfliltered_list if self._filter(obj)]

        else:
            self._object_ids = [object_id]

            self._object_list = [
                ca.GetDalObjectAction(self._application_controller.buffer_daq_config)(
                    object_id, self._object_class
                )
                for object_id in self._object_ids
                if self._filter(
                    ca.GetDalObjectAction(
                        self._application_controller.buffer_daq_config
                    )(object_id, self._object_class)
                )
            ]

        # Get the object IDs for the objects in the list and store
        self._object_ids = [
            ca.GetAttributeAction(self._application_controller.buffer_daq_config)(
                obj, "id"
            )
            for obj in self._object_list
        ]

        self._lower_limit, self._upper_limit = self._range()

        # Store initial values for the attribute [convert for hex for simplicity]
        for obj in self._object_list:
            val = ca.GetAttributeAction(self._application_controller.buffer_daq_config)(
                obj, self._attribute_name
            )

            if self._is_hex:
                val = self.convert_from_hex(val)

            self._init_values[
                ca.GetAttributeAction(self._application_controller.buffer_daq_config)(
                    obj, "id"
                )
            ] = val

        self._tooltip_var = kwargs.get("tooltip", None)

    def set_state(self, object_id: str, value) -> None:
        """
        Set the attribute value for all objects in the object list.
        """
        if object_id not in self._object_ids:
            logging.debug(f"Object ID {object_id} not found in object list.")
            raise ValueError(f"Object ID {object_id} not found in object list.")

        if isinstance(value, float):
            value = value * self._unit_scale

        # Convert value to hexadecimal if required
        if self._is_hex:
            value = self.convert_to_hex(value)

        if (
            self._upper_limit is not None
            and self._lower_limit is not None
            and isinstance(value, float | int)
        ):
            if value < self._lower_limit or value > self._upper_limit:
                raise CiderOutOfBoundsException(
                    f"Value {value} exceeds bounds {self._lower_limit}, {self._upper_limit}."
                )

        for obj in self._object_list:
            if (
                not ca.GetAttributeAction(
                    self._application_controller.buffer_daq_config
                )(obj, "id")
                == object_id
            ):
                continue

            logging.debug(
                f"Setting attribute {self._attribute_name} for object {object_id} to value {value}"
            )

            ca.ChangeAttributeAction(self._application_controller.buffer_daq_config)(
                obj, self._attribute_name, value
            )

            ca.UpdateDalAction(self._application_controller.buffer_daq_config)(obj)

    def get_state(self, object_id: str):
        """
        Get state of the attribute for a given object ID.
        :param object_id: The ID of the object to get the state for.
        :return: The value of the attribute for the object, converted to hertz if required.
        """
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

                if isinstance(attr_value, float):
                    attr_value *= self._unit_scale

                if self._is_hex:
                    attr_value = self.convert_from_hex(attr_value)

                return attr_value

        return None

    def get_object_list(self) -> list[str]:
        """
        Get the list of object IDs for which the attribute can be set.
        """
        return self._object_ids

    def get_all_states(self) -> dict:
        """
        Get state of the attribute for all objects in the object list, sorted by object ID (natural sort).
        """

        def natural_key(s):
            # Split string into list of strings and integers for natural sorting
            return [
                int(text) if text.isdigit() else text for text in re.split(r"(\d+)", s)
            ]

        sorted_ids = sorted(self._object_ids, key=natural_key)
        return {
            obj: {"state": self.get_state(obj), "attribute": self._attribute_name}
            for obj in sorted_ids
        }

    def get_tooltip(self, object_id) -> str | None:
        if object_id not in self._object_ids:
            logging.debug(f"Object ID {object_id} not found in object list.")
            return None

        if self._tooltip_var is None:
            return f"Adjust [bold]{self._attribute_name}[/bold] for [bold]{object_id}[/bold] of class [bold]{self._object_class}[/bold]"

        dal_obj = ca.GetDalObjectAction(self._application_controller.buffer_daq_config)(
            object_id, self._object_class
        )
        return ca.GetAttributeAction(self._application_controller.buffer_daq_config)(
            dal_obj, self._tooltip_var
        )

    def get_value_label(self, object_id: str) -> str:
        """
        Get the tooltip for the attribute value of a given object ID.
        """
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
            attribute_value = f"{attribute_value:.3f}"

        if self._is_hex:
            attribute_value = self.convert_from_hex(attribute_value)

        tooltip = f"{attribute_value} {self._unit_label}"

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

    def convert_to_hex(self, value: int) -> str:
        # Convert an integer value to hexadecimal format
        return hex(int(value))

    def convert_from_hex(self, value: str) -> int:
        # Convert a hexadecimal string to an integer
        if value.startswith("0x"):
            return int(value, 16)
        raise ValueError(f"Invalid hexadecimal value: {value}")

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
        self.set_state(object_id, init_value)

    @property
    def upper_limit(self) -> float | None:
        return self._upper_limit

    @property
    def lower_limit(self) -> float | None:
        return self._lower_limit

    @property
    def attribute_name(self) -> str | None:
        return self._attribute_name

    @property
    def class_name(self) -> str | None:
        return self._object_class

    def _range(self) -> tuple[float, float] | tuple[None, None]:
        """
        Get the range of the attribute.
        Returns a tuple of (lower_limit, upper_limit).
        If limits are not set, returns (None, None).
        """
        range_str = ca.GetConfigAttributePropertiesAction(
            self._application_controller.buffer_daq_config
        )(self._object_class, self._attribute_name).get("range", None)

        if range_str is None or range_str == "None":
            return None, None

        upper, lower = range_str.split("..")

        return float(lower), float(upper)

    def _filter(self, obj) -> bool:
        """
        Filter objects based on the filter_by attribute.
        Returns True if the object matches the filter criteria, False otherwise.
        """
        if not self._filter_by:
            return True

        for filter in self._filter_by:
            attr_name = filter["attribute"]
            values = filter["values"]
            if (
                ca.GetAttributeAction(self._application_controller.buffer_daq_config)(
                    obj, attr_name
                )
                in values
            ):
                return False

        return True
