from pathlib import Path

import yaml
from conffwk import Configuration

from runconf_ui.system_configuration.config_assembler import ConfigAssembler

from .config_dataclasses import (
    AdjustableGroupData,
    DisableableGroupData,
    YamlToSystemData,
)

# ============================================================
# CONFIG LAYER
# ============================================================

class SystemConfig:
    """Loads and exposes structured visibility configuration."""

    def __init__(self, path: Path):
        # purly for testing
        self.path = path
        self._raw = self._load(path)

        # Fully structured representation
        self._settings = YamlToSystemData.build_settings(self._raw)
        self._disableable = YamlToSystemData.build_disableable_groups(
            self._raw.get("PanelOptions", {})
        )
        self._adjustable = YamlToSystemData.build_adjustable_groups(
            self._raw.get("AdjustableAttributes", {})
        )

    @staticmethod
    def _load(path: Path) -> dict:
        with open(path) as f:
            return yaml.safe_load(f)


    @property
    def classes_to_show(self) -> list[str]:
        return self._settings.classes_to_show

    @property
    def adjustable_skeleton(self)->dict[str, AdjustableGroupData]:
        return self._adjustable

    @property
    def disableable_skeleton(self)->dict[str, DisableableGroupData]:
        return self._disableable

class SystemConfigReader:
    """Facade that coordinates config reading + building of StateOperations."""

    def __init__(self, config_path: Path):
        self.config = SystemConfig(config_path)

    def assemble_config(
        self,
        configuration: Configuration,
        session_name: str,
    ):
        '''
        Gets the full operations tree for a given configuration  
        '''
        
        session = configuration.get_dal("Session", session_name)

        builder = ConfigAssembler(configuration, session)

        return  {
            "disableable": builder.assemble_config(self.config.disableable_skeleton, 'disableable'),
            "adjustable": builder.assemble_config(self.config.adjustable_skeleton, 'adjustable'),
        }
