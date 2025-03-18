"""
Simple wrapper for talking to config-management
"""

from config_management.ConfPool import ConfPool
from cider.utils.shifter_config_reader import ShifterConfigReader
import re


class ManagementInterface:
    def __init__(self, interface_config: ShifterConfigReader) -> None:

        self._pool = ConfPool(interface_config.download_directory,
                              operation_url=interface_config.operation_url,
                              base_url=interface_config.base_url)
        self._release = None
        self._release_str = None

    def get_config_version(self):
        return self._pool.get_daq_versions()

    @property
    def release(self) -> re.Pattern | None:
        return self._release

    @release.setter
    def release(self, release: str | None) -> None:
        if release is None:
            self._release = None
            return

        self._release_str = release
        self._release = re.compile(release)

    def get_confs(self):
        if self._release is None:
            return []
        return self._pool.get_confs(self._release)

    def checkout_conf(self, config):
        if self._release is None:
            return None
        self._pool.checkout_conf(config, str(self._release_str))
