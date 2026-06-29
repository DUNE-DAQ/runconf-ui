from pathlib import Path

from runconf_ui.exceptions import RunConfToolsRepoException

from .detail import LocalRepoManager, RemoteRepoManager, EmulationRepoManager
from .repo_manager_interface import RepoManagerInterface

from enum import Enum

class RepoManagerType(Enum) :
    LOCAL = "local"
    REMOTE = "remote"
    EMULATION = "emulation"

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
    repo_type : RepoManagerType,
    config_file_name: str | None = None,
    ops_url: str | None = None,
    base_url: str | None = None,
) -> RepoManagerInterface:
    """
    Factory for the repo maanger

    :param apparatus: Apparatus used
    :type apparatus: str
    :param conf_directory: Config directory
    :type conf_directory: Path
    :param use_local: Use a local configuration?, defaults to False
    :type use_local: bool, optional
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

    if repo_type.value == "local"  :
        return LocalRepoManager(apparatus, conf_directory, config_file_name)
    if ops_url is None:
        raise RunConfToolsRepoException(
            f"Error {ops_url} not set, cannot use Runconftool interface"
        )
    if base_url is None:
        raise RunConfToolsRepoException(
            f"Error {base_url} not set, cannot use Runconftool interface"
        )

    if repo_type.value == "emulation" :
        return EmulationRepoManager(
            apparatus=apparatus,
            conf_directory=conf_directory,
            config_file_name=config_file_name,
            operation_url=ops_url,
            base_url=base_url,
        )

    
    if config_file_name is None:
        raise RunConfToolsRepoException(
            f"Error {config_file_name} not set, cannot use remote interface"
        )

    if repo_type.value == "remote" :
        return RemoteRepoManager(
            apparatus=apparatus,
            conf_directory=conf_directory,
            config_file_name=config_file_name,
            operation_url=ops_url,
            base_url=base_url,
        )
    
 
