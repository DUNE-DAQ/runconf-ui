'''
Dataclasses for systems in the configuration. Much neater than passing dicts
'''

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar('T')


@dataclass(kw_only=True)
class FilterData:
    attribute: str
    values: list[Any]


@dataclass(kw_only=True)
class SystemElementData:
    class_name: str
    id: str = ""
    system_label: str = ""
    filters: list[FilterData] = field(default_factory=list)


@dataclass(kw_only=True)
class DisableElementData(SystemElementData):
    separate_system: bool = False
    each_component_separate: bool = False


@dataclass(kw_only=True)
class _DisableAttributeGenericData(DisableElementData, Generic[T]):
    enabled_state: T = True
    disabled_state: T = False
    segments: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class DisableAttributeData(_DisableAttributeGenericData[Any]):
    ...


@dataclass(kw_only=True)
class DisableRelationshipData(_DisableAttributeGenericData[str | list[str]]):
    relationship_class: str = ""


@dataclass(kw_only=True)
class AdjustableAttributeData(SystemElementData):
    attribute_name: str = ""
    unit_label: str = ""


@dataclass
class DisableableSystemData:
    subsystem_dependent: bool
    display_full_system: bool
    components: list[DisableElementData]
    attributes: list[DisableAttributeData]
    relationships: list[DisableRelationshipData]


@dataclass
class DisableableGroupData:
    label: str
    view_panel: str
    systems: dict[str, list[DisableableSystemData]]


@dataclass
class AdjustableGroupData:
    label: str
    systems: dict[str, list[AdjustableAttributeData]]


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
    return [FilterData(attribute=r['attribute'], values=r['values']) for r in (raw or [])]


def _base_disable_kwargs(item: dict) -> dict:
    return dict(
        class_name=item["class"],
        id=item.get("id", ""),
        system_label=item.get("system_label", ""),
        filters=_filters(item.get("filters"),),
        separate_system=item.get("separate_system", False),
        each_component_separate=item.get("each_component_separate", False),
    )


def _attribute_kwargs(item: dict) -> dict:
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
        return {
            name: AdjustableGroupData(
                label=data.get("label", ""),
                systems=cls._build_adjustable_systems(data.get("Systems", [])),
            )
            for name, data in raw.items()
        }

    @staticmethod
    def build_settings(raw: dict) -> SettingsData:
        return SettingsData(classes_to_show=raw.get("Settings", {}).get("classes_to_show", []))

    @classmethod
    def _build_disableable_systems(cls, raw_systems: list[dict]) -> dict[str, list[DisableableSystemData]]:
        systems: dict[str, list[DisableableSystemData]] = {}
        for entry in raw_systems:
            for name, data in entry.items():
                system = DisableableSystemData(
                    subsystem_dependent=data.get("subsystem_dependent", False),
                    display_full_system=data.get("display_full_system", False),
                    components=[DisableElementData(**_base_disable_kwargs(i)) for i in data.get("components", [])],
                    attributes=[DisableAttributeData(**_attribute_kwargs(i)) for i in data.get("attributes", [])],
                    relationships=cls._build_relationships(data.get("relationships", [])),
                )
                systems.setdefault(name, []).append(system)
        return systems

    @staticmethod
    def _build_relationships(raw) -> list[DisableRelationshipData]:
        if isinstance(raw, dict):
            raw = [raw]
        return [
            DisableRelationshipData(**_attribute_kwargs(i), relationship_class=i.get("relationship_class", ""))
            for i in raw
        ]

    @staticmethod
    def _build_adjustable_systems(raw_systems: list[dict]) -> dict[str, list[AdjustableAttributeData]]:
        '''
        NOTE: For adjustable attributes we add a dummy "default"
        This is because I
        '''
        attrs = [
            AdjustableAttributeData(
                class_name=entry["object_class"],
                id=entry.get("object_id", ""),
                filters=_filters(entry.get("filters")),
                attribute_name=entry["attribute_name"],
                unit_label=entry.get("unit_label", ""),
            )
            for entry in raw_systems
        ]
        return {"default": attrs} if attrs else {}