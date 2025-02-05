import os
from typing import Any, Dict, List

import conffwk

"""
HW: Augment configuration with additional wrapper layer
"""


class ConfigurationWrapper(conffwk.Configuration):
    def __init__(self, configuration_file_path: str):
        super().__init__(f"oksconflibs:{configuration_file_path}")

        self._file_name: str = configuration_file_path

    @property
    def file_name(self) -> str:
        return self._file_name
