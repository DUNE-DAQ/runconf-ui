"""
Simple wrapper for talking to config-management
"""

from config_management.ConfPool import ConfPool
import re


class ManagementInterface:
    def __init__(
        self,
        path,
        base="ssh://git@gitlab.cern.ch:7999/dune-daq/online/ehn1-daqconfigs.git",
        operation="ssh://git@gitlab.cern.ch:7999/dune-daq/online/np02-configs-operation.git",
    ) -> None:

        self._pool = ConfPool(path, operation_url=operation, base_url=base)
        self._release = None
        self._release_str = None

    def get_base_branches(self):
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
