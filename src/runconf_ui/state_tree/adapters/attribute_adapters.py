from typing import Any

from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.exceptions import AttributeMissingException

from .adapter import Adapter


class DisableAttribute(Adapter):
    """Adapter for toggling DAL objects by enabling/disabling a named attribute.

    Also considers the DAL's own resource-disabled state: if the DAL is
    disabled as a resource, this attribute is considered disabled regardless
    of its stored value.
    """

    def __init__(
        self,
        configuration: Configuration,
        session: DalBase,
        dal: DalBase,
        attribute_name: str,
        enabled_value: Any = True,
        disabled_value: Any = False,
    ):
        """Initialize a DisableAttribute adapter.

        :param configuration: The Configuration object
        :param session: The session DAL
        :param dal: The DAL object to manage
        :param attribute_name: Name of the attribute that controls enable/disable
        :param enabled_value: Value that represents enabled state
        :param disabled_value: Value that represents disabled state
        :raises AttributeMissingException: If the attribute does not exist on the DAL
        """
        if not hasattr(dal, attribute_name):
            raise AttributeMissingException(
                f"{dal!r} does not have attribute {attribute_name!r}"
            )
        super().__init__(configuration, session, dal)
        self.attribute_name = attribute_name
        self.enabled_value = enabled_value
        self.disabled_value = disabled_value

    def get(self) -> bool:
        """Get the enabled state of the attribute.

        :returns: True if attribute equals enabled_value and DAL is enabled as resource
        :rtype: bool
        """
        return (
            getattr(self.dal, self.attribute_name) == self.enabled_value
            and self.dal_enabled()
        )

    def set(self, value: bool) -> None:
        """Set the enabled state by toggling the attribute value.

        :param value: True to set enabled_value, False to set disabled_value
        """
        new_value = self.enabled_value if value else self.disabled_value
        if getattr(self.dal, self.attribute_name) != new_value:
            setattr(self.dal, self.attribute_name, new_value)
            self.configuration.update_dal(self.dal)


class AdjustableAttribute(Adapter):
    """Adapter for reading and writing any-valued attributes.

    Used for adjustable values like trigger rates, thresholds, or other
    configuration parameters that can take any value, not just boolean.
    """

    def __init__(
        self,
        configuration: Configuration,
        session: DalBase,
        dal: DalBase,
        attribute_name: str,
    ):
        """Initialize an AdjustableAttribute adapter.

        :param configuration: The Configuration object
        :param session: The session DAL
        :param dal: The DAL object to manage
        :param attribute_name: Name of the adjustable attribute
        :raises AttributeMissingException: If the attribute does not exist on the DAL
        """
        if not hasattr(dal, attribute_name):
            raise AttributeMissingException(
                f"{dal!r} does not have attribute {attribute_name!r}"
            )
        super().__init__(configuration, session, dal)
        self.attribute_name = attribute_name

    def get(self) -> Any:
        """Get the current attribute value.

        :returns: The attribute value
        """
        return getattr(self.dal, self.attribute_name)

    def set(self, value: Any) -> None:
        """Set the attribute value.

        :param value: The new value to set
        """
        if getattr(self.dal, self.attribute_name) != value:
            setattr(self.dal, self.attribute_name, value)
            self.configuration.update_dal(self.dal)
