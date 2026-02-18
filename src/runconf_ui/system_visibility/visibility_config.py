from pathlib import Path

import yaml
from conffwk import Configuration

from runconf_ui.system_visibility.system_builders import OperationsTreeBuilder

# ============================================================
# CONFIG LAYER
# ============================================================

class VisibilityConfig:
    """Loads and exposes structured visibility configuration."""

    def __init__(self, path: Path):
        # purly for testing
        self.path = path
        self._raw = self._load(path)

    @staticmethod
    def _load(path: Path) -> dict:
        with open(path) as f:
            return yaml.safe_load(f)

    @property
    def classes_to_show(self) -> str:
        return self._raw.get("Settings", {}).get("classes_to_show", "")

    @property
    def adjustable_skeleton(self) -> dict:
        return self._raw.get("AdjustableAttributes", {})

    @property
    def disableable_skeleton(self) -> dict:
        return self._raw.get("PanelOptions", {})


class VisibilityConfigReader:
    """Facade that coordinates config + tree building."""

    def __init__(self, config_path: Path):
        self.config = VisibilityConfig(config_path)

    def generate_operations_tree(
        self,
        configuration: Configuration,
        session_name: str,
    ):
        session = configuration.get_dal("Session", session_name)

        builder = OperationsTreeBuilder(configuration, session)

        return {
            "disableable": builder.build(self.config.disableable_skeleton),
            "adjustable": builder.build(self.config.adjustable_skeleton),
        }
