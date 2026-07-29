from enum import Enum
from pathlib import Path
from typing import Any

from runconf_ui.exceptions import RunConfToolsRepoException

from .detail import EmulationRepoManager, LocalRepoManager, RemoteRepoManager
from .repo_manager_interface import RepoManagerInterface


class RepoManagerType(Enum):
    LOCAL = "local"
    REMOTE = "remote"

    def __str__(self):
        return self.value

    @classmethod
    def from_string(cls, s: str) -> "RepoManagerType":
        try:
            return cls(s)
        except ValueError:
            raise ValueError(f"{s!r} is not a valid {cls.__name__}")

    @classmethod
    def values(cls) -> list[str]:
        return [c.value for c in cls]


def repo_factory(
    apparatus: str,
    conf_directory: Path,
    repo_type: RepoManagerType,
    config_file_name: str | None = None,
    ops_url: str | None = None,
    base_url: str | None = None,
) -> RepoManagerInterface[Any]:
    """
    Factory for the repo maanger

    :param apparatus: Apparatus used
    :type apparatus: str
    :param conf_directory: Config directory
    :type conf_directory: Path
    :param repo_type : specifies the type of the repo manager to instantiate
    :type repo_type:  RepoManagerType
    :param config_file_name: The config file name, defaults to None
    :type config_file_name: Optional[str], optional
    :param ops_url: The operation URL, defaults to None
    :type ops_url: Optional[str], optional
    :param base_url: The Base url, defaults to None
    :type base_url: Optional[str], optional
    :raises RunConfToolsRepoException: No config file set
    :raises RunConfToolsRepoException: No ops repo set
    :raises RunConfToolsRepoException: No base repo set
    :return: the repo manager
    :rtype: RepoManagerInterface
    """

    if repo_type == RepoManagerType.LOCAL:
        return LocalRepoManager(apparatus, conf_directory, config_file_name)
    
    if ops_url is None:
        raise RunConfToolsRepoException(
            "Error ops_url not set, cannot use Runconftool interface"
        )
    if base_url is None:
        raise RunConfToolsRepoException(
            "Error base_url not set, cannot use Runconftool interface"
        )

    if config_file_name is None:
        raise RunConfToolsRepoException(
            f"Error {config_file_name} not set, cannot use remote interface"
        )

    return RemoteRepoManager(
        apparatus=apparatus,
        conf_directory=conf_directory,
        config_file_name=config_file_name,
        operation_url=ops_url,
        base_url=base_url,
    )
