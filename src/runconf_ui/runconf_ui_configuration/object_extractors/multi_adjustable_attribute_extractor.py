from runconf_ui.runconf_ui_configuration.object_extractors.adjustable_attribute_extractor import (
    AdjustableAttributeManager,
)
import runconf_ui.daq_config_interfaces.actions.actions as ca

import logging
from traceback import format_exc

class MultiAdjustableAttributeExtractor:
    def __init__(self, application_controller, **kwargs):
        """
        Initializes the MultiAdjustableAttributeExtractor with the application controller and adjustable attributes.
        :param application_controller: The application controller instance.
        :param kwargs: Additional keyword arguments for adjustable attributes.
        """
        self._application_controller = application_controller

        self._adjustable_attributes = []
        for obj in kwargs["Systems"]:
            try:
                self._adjustable_attributes.append(
                    AdjustableAttributeManager(self._application_controller, **obj)
                )
            except:
                logging.debug(
                    f"Failed to initialize AdjustableAttributeManager with {obj}."
                )
                logging.debug(f"Error: {format_exc()}")

    def set_state(self, object_id: str, attribute_name: str, value: float):
        """
        Sets the specified attribute for the given object ID.
        :param object_id: The ID of the object to set the attribute for.
        :param attribute_name: The name of the attribute to set.
        :param value: The value to set for the attribute.
        """
        for manager in self._adjustable_attributes:
            if (
                object_id in manager.get_all_states()
                and attribute_name == manager.attribute_name
            ):
                manager.set_state(object_id, value)
                return
        raise ValueError(
            f"Object ID {object_id} or attribute {attribute_name} not found in adjustable attributes."
        )

    def get_state(self, object_id: str, attribute_name: str) -> float:
        """
        Gets the specified attribute for the given object ID.
        :param object_id: The ID of the object to get the attribute for.
        :param attribute_name: The name of the attribute to get.
        :return: The value of the specified attribute.
        """
        for manager in self._adjustable_attributes:
            if (
                object_id in manager.get_all_states()
                and attribute_name == manager.attribute_name
            ):
                return manager.get_state(object_id)
        raise ValueError(
            f"Object ID {object_id} or attribute {attribute_name} not found in adjustable attributes."
        )

    def get_all_states(self) -> dict:
        """
        Gets all adjustable attributes and their states.
        :return: A dictionary of object IDs and their corresponding attribute states.
        """
        all_attributes = {}
        for manager in self._adjustable_attributes:
            all_attributes.update(manager.get_all_states())
        return all_attributes

    def reset_attribute(self, object_id: str, attribute_name: str):
        """
        Resets the specified attribute for the given object ID to its initial value.
        :param object_id: The ID of the object to reset the attribute for.
        :param attribute_name: The name of the attribute to reset.
        """
        for manager in self._adjustable_attributes:
            if (
                object_id in manager.get_all_states()
                and attribute_name == manager.attribute_name
            ):
                manager.reset_value(object_id)
                return

    def get_value_label(self, object_id: str, attribute_name: str) -> str | None:
        """
        Gets the tooltip for the specified attribute of the given object ID.
        :param object_id: The ID of the object to get the tooltip for.
        :param attribute_name: The name of the attribute to get the tooltip for.
        :return: The tooltip string for the specified attribute.
        """
        for manager in self._adjustable_attributes:
            if (
                object_id in manager.get_all_states()
                and attribute_name == manager.attribute_name
            ):
                return manager.get_value_label(object_id)

    def get_tooltip(self, object_id: str, attribute_name: str) -> str | None:
        """
        Gets the tooltip for the specified attribute of the given object ID.
        :param object_id: The ID of the object to get the tooltip variable for.
        :param attribute_name: The name of the attribute to get the tooltip variable for.
        :return: The tooltip variable string for the specified attribute.
        """
        for manager in self._adjustable_attributes:
            if (
                object_id in manager.get_all_states()
                and attribute_name == manager.attribute_name
            ):
                return manager.get_tooltip(object_id)
                                

    def lower_limit(self, object_id: str, attribute_name: str) -> float | None:
        """
        Gets the lower limit for the specified attribute of the given object ID.
        :param object_id: The ID of the object to get the lower limit for.
        :param attribute_name: The name of the attribute to get the lower limit for.
        :return: The lower limit value or None if not set.
        """
        for manager in self._adjustable_attributes:
            if (
                object_id in manager.get_all_states()
                and attribute_name == manager.attribute_name
            ):
                return manager.lower_limit

    def upper_limit(self, object_id: str, attribute_name: str) -> float | None:
        """
        Gets the upper limit for the specified attribute of the given object ID.
        :param object_id: The ID of the object to get the upper limit for.
        :param attribute_name: The name of the attribute to get the upper limit for.
        :return: The upper limit value or None if not set.
        """
        for manager in self._adjustable_attributes:
            if (
                object_id in manager.get_all_states()
                and attribute_name == manager.attribute_name
            ):
                return manager.upper_limit

    def reset_value(self, object_id: str, attribute_name: str):
        """
        Resets all adjustable attributes for the given object ID to their initial values.
        :param object_id: The ID of the object to reset.
        """
        for manager in self._adjustable_attributes:
            if (
                object_id in manager.get_all_states()
                and attribute_name == manager.attribute_name
            ):
                manager.reset_value(object_id)
            else:
                logging.debug(
                    f"Object ID {object_id} not found in adjustable attributes."
                )
