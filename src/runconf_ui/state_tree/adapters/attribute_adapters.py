from typing import Any

from conffwk import Configuration
from conffwk.dal import DalBase

from runconf_ui.exceptions import AttributeMissingException

from .adapter import Adapter


class DisableAttribute(Adapter):
    """
    Enables/disables a DAL object by toggling a named attribute.

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
        if not hasattr(dal, attribute_name):
            raise AttributeMissingException(
                f"{dal!r} does not have attribute {attribute_name!r}"
            )
        super().__init__(configuration, session, dal)
        self.attribute_name = attribute_name
        self.enabled_value = enabled_value
        self.disabled_value = disabled_value

    def get(self) -> bool:
        return (
            getattr(self.dal, self.attribute_name) == self.enabled_value
            and self.dal_enabled()
        )

    def set(self, value: bool) -> None:
        new_value = self.enabled_value if value else self.disabled_value
        if getattr(self.dal, self.attribute_name) != new_value:
            setattr(self.dal, self.attribute_name, new_value)
            self.configuration.update_dal(self.dal)


class AdjustableAttribute(Adapter):
    """
    Reads and writes an attribute that can take any value, not just bool.
    Used for things like trigger rates.
    """

    def __init__(
        self,
        configuration: Configuration,
        session: DalBase,
        dal: DalBase,
        attribute_name: str,
    ):
        if not hasattr(dal, attribute_name):
            raise AttributeMissingException(
                f"{dal!r} does not have attribute {attribute_name!r}"
            )
        super().__init__(configuration, session, dal)
        self.attribute_name = attribute_name

    def get(self) -> Any:
        return getattr(self.dal, self.attribute_name)

    def set(self, value: Any) -> None:
        if getattr(self.dal, self.attribute_name) != value:
            setattr(self.dal, self.attribute_name, value)
            self.configuration.update_dal(self.dal)
