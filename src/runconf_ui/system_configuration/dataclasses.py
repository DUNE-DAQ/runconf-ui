"""
Dataclasses for systems in the configuration. Much neater than passing dicts
"""

from dataclasses import dataclass, field
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass(kw_only=True)
class FilterData:
    """For the Filters attribute"""

    attribute: str  # Name of the attribute to filter on
    values: list[Any]  # Values of the attribute to filter out


@dataclass(kw_only=True)
class SystemElementData:
    """Any "system element" will use this info"""

    class_name: str  # Class of the DAL object in the system
    id: str = ""  # id of the system element
    system_label: str = ""  # Label of the system element
    filters: list[FilterData] = field(default_factory=list)  # Any filters
    tooltip: str = ""  # Tooltip shown on hover in the UI


@dataclass(kw_only=True)
class DisableElementData(SystemElementData):
    """Anything that can be disabled also has this"""

    each_component_separate: bool = False  # Is each component a separate subsystem
    separate_system: bool = False  # Does this by itself comprise a seperate subsystem


@dataclass(kw_only=True)
class DisableAttributeData(DisableElementData):
    """Attributes that can be disabled use this"""

    enabled_state: Any = True  # Enabled value
    disabled_state: Any = False  # Disabled value
    segments: list[str] = field(default_factory=list)  # Segments to search


@dataclass(kw_only=True)
class DisableRelationshipData(DisableAttributeData):
    """Relationships also need to know the class of the related object(s)
    For relationships the enabled/disabled states should be (lists of) dal object ids
    """

    relationship_class: str = ""  # Class of disabled/enabled DAL objects


@dataclass(kw_only=True)
class AdjustableAttributeData(SystemElementData):
    """Adjustable attributes have some "funky" features"""

    attribute_name: str = ""  # Name of the attribute
    unit_label: str = ""  # Units of the attribute (Hz, ticks, etc.)


@dataclass
class DisableableSystemData:
    """Systems of disabled elements"""

    subsystem_dependent: bool  # Does this system depend soley on its subsystems
    display_full_system: bool  # Do you want to display the top-level-system?
    components: list[DisableElementData]  # Components in the system
    attributes: list[DisableAttributeData]  # Attributes in the system
    relationships: list[DisableRelationshipData]  # Relationships in the system


@dataclass
class DisableableGroupData:
    label: str  # Internal label of the group
    view_panel: str  # Tag for the view panel
    systems: dict[str, list[DisableableSystemData]]  # Any internal systems


@dataclass
class AdjustableGroupData:
    label: str  # Label of the group
    systems: dict[str, list[AdjustableAttributeData]]  # Any internal systems


@dataclass
class PanelOptionsData:
    panels: dict[str, DisableableGroupData]


@dataclass
class AdjustableAttributesData:
    groups: dict[str, AdjustableGroupData]


@dataclass
class SettingsData:
    classes_to_show: list[str]


@dataclass
class SystemConfigData:
    settings: SettingsData
    panel_options: PanelOptionsData
    adjustable_attributes: AdjustableAttributesData


# ── Helpers ────────────────────────────────────────────────────────────────────


def _filters(raw) -> list[FilterData]:
    """Convert raw filter dictionaries to FilterData objects.

    :param raw: Raw filter data list from YAML
    :returns: List of FilterData objects
    :rtype: list[FilterData]
    """
    return [
        FilterData(attribute=r["attribute"], values=r["values"]) for r in (raw or [])
    ]


def _base_disable_kwargs(item: dict) -> dict:
    """Extract base disable element kwargs from a raw dictionary.

    :param item: Raw item dictionary from YAML
    :returns: Dictionary of keyword arguments for DisableElementData
    :rtype: dict
    """
    return dict(
        class_name=item["class"],
        id=item.get("id", ""),
        system_label=item.get("system_label", ""),
        filters=_filters(
            item.get("filters"),
        ),
        separate_system=item.get("separate_system", False),
        each_component_separate=item.get("each_component_separate", False),
        tooltip=item.get("tooltip", ""),
    )


def _attribute_kwargs(item: dict) -> dict:
    """Extract disable attribute kwargs from a raw dictionary.

    :param item: Raw item dictionary from YAML
    :returns: Dictionary of keyword arguments for DisableAttributeData
    :rtype: dict
    """
    return dict(
        **_base_disable_kwargs(item),
        enabled_state=item.get("enabled_state", True),
        disabled_state=item.get("disabled_state", False),
        segments=item.get("segments", []),
    )


# ── YamlToSystemData ───────────────────────────────────────────────────────────


class YamlToSystemData:
    """Converts raw YAML dictionaries into structured dataclasses."""

    @classmethod
    def build_disableable_groups(cls, raw: dict) -> dict[str, DisableableGroupData]:
        """Build disableable group dataclass objects from raw YAML data.

        :param raw: Raw YAML dictionary containing disableable group data
        :returns: Dictionary mapping group names to DisableableGroupData objects
        :rtype: dict[str, DisableableGroupData]
        """
        return {
            name: DisableableGroupData(
                label=data.get("label", ""),
                view_panel=data.get("view_panel", ""),
                systems=cls._build_disableable_systems(data.get("Systems", [])),
            )
            for name, data in raw.items()
        }

    @classmethod
    def build_adjustable_groups(cls, raw: dict) -> dict[str, AdjustableGroupData]:
        """Build adjustable group dataclass objects from raw YAML data.

        :param raw: Raw YAML dictionary containing adjustable group data
        :returns: Dictionary mapping group names to AdjustableGroupData objects
        :rtype: dict[str, AdjustableGroupData]
        """
        return {
            name: AdjustableGroupData(
                label=data.get("label", ""),
                systems=cls._build_adjustable_systems(data.get("Systems", []), name),
            )
            for name, data in raw.items()
        }

    @staticmethod
    def build_settings(raw: dict) -> SettingsData:
        """Build settings dataclass from raw YAML data.

        :param raw: Raw YAML dictionary containing settings data
        :returns: SettingsData object
        :rtype: SettingsData
        """
        return SettingsData(
            classes_to_show=raw.get("Settings", {}).get("classes_to_show", [])
        )

    @classmethod
    def _build_disableable_systems(
        cls, raw_systems: list[dict]
    ) -> dict[str, list[DisableableSystemData]]:
        """Build disableable system dataclass objects from raw YAML data.

        :param raw_systems: List of raw system dictionaries from YAML
        :returns: Dictionary mapping system names to lists of DisableableSystemData
        :rtype: dict[str, list[DisableableSystemData]]
        """
        systems: dict[str, list[DisableableSystemData]] = {}
        for entry in raw_systems:
            for name, data in entry.items():
                system = DisableableSystemData(
                    subsystem_dependent=data.get("subsystem_dependent", False),
                    display_full_system=data.get("display_full_system", True),
                    components=[
                        DisableElementData(**_base_disable_kwargs(i))
                        for i in data.get("components", [])
                    ],
                    attributes=[
                        DisableAttributeData(**_attribute_kwargs(i))
                        for i in data.get("attributes", [])
                    ],
                    relationships=cls._build_relationships(
                        data.get("relationships", [])
                    ),
                )
                systems.setdefault(name, []).append(system)
        return systems

    @staticmethod
    def _build_relationships(raw) -> list[DisableRelationshipData]:
        """Build relationship dataclass objects from raw YAML data.

        :param raw: Raw relationship data (dict or list of dicts)
        :returns: List of DisableRelationshipData objects
        :rtype: list[DisableRelationshipData]
        """
        if isinstance(raw, dict):
            raw = [raw]
        return [
            DisableRelationshipData(
                **_attribute_kwargs(i),
                relationship_class=i.get("relationship_class", ""),
            )
            for i in raw
        ]

    @staticmethod
    def _build_adjustable_systems(
        raw_systems: list[dict], name: str
    ) -> dict[str, list[AdjustableAttributeData]]:
        """Build adjustable attribute system dataclass objects from raw YAML data.

        :param raw_systems: List of raw system dictionaries from YAML
        :param name: The system group name
        :returns: Dictionary mapping system name to list of AdjustableAttributeData
        :rtype: dict[str, list[AdjustableAttributeData]]
        """
        attrs = [
            AdjustableAttributeData(
                class_name=entry["object_class"],
                id=entry.get("object_id", ""),
                filters=_filters(entry.get("filters")),
                attribute_name=entry["attribute_name"],
                unit_label=entry.get("unit_label", ""),
                tooltip=entry.get("tooltip", ""),
            )
            for entry in raw_systems
        ]
        return {name: attrs} if attrs else {}
