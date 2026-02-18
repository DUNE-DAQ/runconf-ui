from typing import Any

from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.exceptions import AttributeMissingException, AttributeValueException
from runconf_ui.state_operations.state_operation import DisableOperation, StateOperation


class DalAttribute:
    """
    A set of methods for handling attributes in a DAL
    """

    def _init_attribute(
        self,
        configuration: Configuration,
        session: DalBase,
        dal: DalBase,
        attribute_name: str,
    ):
        self.dal = dal
        self.attribute_name = attribute_name
        self.configuration = configuration
        self.session = session

        if not hasattr(dal, attribute_name):
            raise AttributeMissingException(
                f"{dal!r} does not have attribute {attribute_name}!"
            )

    def dal_enabled(self) -> bool:
        """Check if the connect DAL object is enabled/disabled"""
        return self.dal not in self.session.disabled

    def _get_attr(self):
        return getattr(self.dal, self.attribute_name)

    def _set_attr(self, value):
        setattr(self.dal, self.attribute_name, value)
        self.configuration.update_dal(self.dal)


class DisableAttribute(DisableOperation, DalAttribute):
    """An attribute that can be enabled/disabled"""

    def __init__(
        self,
        configuration: Configuration,
        session: DalBase,
        dal: DalBase,
        attribute_name: str,
        enabled_value: Any = True,
        disabled_value: Any = False,
        label="",
    ):
        super().__init__(configuration, session, label)
        self._init_attribute(configuration, session, dal, attribute_name)

        self.enabled_value = enabled_value
        self.disabled_value = disabled_value

    def _check_value_valid(self, value):
        if value not in (self.enabled_value, self.disabled_value):
            raise AttributeValueException(
                f"{self.attribute_name} in {self.dal!r} "
                f"must be {self.enabled_value}/{self.disabled_value}, "
                f"not {value}"
            )

    def get_state(self) -> bool:
        value = self._get_attr()
        self._check_value_valid(value)
        return value == self.enabled_value and self.dal_enabled()

    def set_state(self, state: bool) -> None:
        self._check_value_valid(state)

        new_value = self.enabled_value if state else self.disabled_value
        if self._get_attr() != new_value:
            self._set_attr(new_value)


class AdjustableAttribute(StateOperation[Any], DalAttribute):
    """An attribute that can be set to any value"""

    def __init__(
        self,
        configuration: Configuration,
        session: DalBase,
        dal: DalBase,
        attribute_name: str,
        label="",
    ):
        super().__init__(configuration, session, label)
        self._init_attribute(configuration, session, dal, attribute_name)

    def get_state(self) -> Any:
        return self._get_attr()

    def set_state(self, value: Any) -> None:
        if self._get_attr() != value:
            self._set_attr(value)
