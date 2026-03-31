"""Utility functions for safely handling OKS configurations."""

import os
import shutil
from pathlib import Path

from conffwk import Configuration
from conffwk.dal import DalBase
from daqconf.consolidate import consolidate_files

from runconf_ui.exceptions import ConfigReadException


def open_configuration(config_path: Path) -> Configuration:
    """Open and return an OKS configuration from the given path.

    :param config_path: Path to the .data.xml OKS configuration file
    :returns: The loaded Configuration object
    :rtype: Configuration
    :raises ConfigReadException: If the file is invalid or cannot be opened
    :raises FileNotFoundError: If the configuration file does not exist
    """
    if not config_path.name.endswith(".data.xml"):
        raise ConfigReadException(
            f"{config_path} is not an OKS .data.xml configuration"
        )

    if not config_path.exists():
        raise FileNotFoundError(f"Cannot find {config_path}")

    try:
        return Configuration(f"oksconflibs:{config_path}")
    except Exception as e:
        raise ConfigReadException(f"Cannot open {config_path}") from e


def copy_and_open_config(original_config: Path, buffer_file: Path):
    """Copy and consolidate a configuration file, then open it.

    :param original_config: Path to the original configuration file
    :param buffer_file: Path where the consolidated copy should be saved
    :returns: The loaded consolidated Configuration object
    :rtype: Configuration
    """
    buffer_file.parent.mkdir(parents=True, exist_ok=True)
    consolidate_files(str(buffer_file), str(original_config))
    return open_configuration(buffer_file)


def get_number_of_sessions(configuration: Configuration) -> int:
    """Return the number of Session DALs in the given configuration.

    :param configuration: The Configuration object to check
    :returns: The count of Session DAL objects
    :rtype: int
    """
    return len(configuration.get_dals("Session"))


def check_config_has_session(config_path: Path) -> bool:
    """Return True if the configuration at the given path contains at least one Session.

    :param config_path: Path to the configuration file to check
    :returns: True if at least one Session DAL exists, False otherwise
    :rtype: bool
    :raises ConfigReadException: If the configuration cannot be read
    """
    try:
        conf = open_configuration(config_path)
    except Exception as e:
        raise ConfigReadException(f"Cannot read configuration at {config_path}") from e

    has_session = get_number_of_sessions(conf) > 0
    conf.unload()
    return has_session


def get_config_paths(config_directory: Path):
    """Get all .data.xml configuration file paths in a directory.

    :param config_directory: Directory to search for configuration files
    :returns: List of paths to .data.xml files
    :rtype: list[Path]
    :raises ValueError: If config_directory is not a directory
    """
    if not config_directory.is_dir():
        raise ValueError("Input must be a directory")

    return [f for f in config_directory.rglob("*.data.xml") if f.is_file()]


def get_configs_with_session(config_paths: list[Path] | Path) -> list[Path]:
    """
    Return all configuration files that contain at least one Session.

    Accepts a single file or directory, or a mixed list of both.
    Recursively searches directories for .data.xml files.

    :param config_paths: Configuration file path(s) or directory path(s)
    :returns: List of configuration files containing sessions
    :rtype: list[Path]
    """
    if isinstance(config_paths, Path):
        config_paths = [config_paths]

    config_files: list[Path] = []

    for path in config_paths:
        if path.is_file() and path.name.endswith(".data.xml"):
            config_files.append(path)
        elif path.is_dir():
            config_files += get_config_paths(path)

    return_paths = []

    for c in config_files:
        try:
            if check_config_has_session(c):
                return_paths.append(c)
        except Exception:
            # Skip files that cannot be read as configurations
            continue

    return return_paths


def get_class_from_segment(
    configuration: Configuration, segment_id: str, class_name: str
):
    """Find all instances of a class in a segment.

    Includes all subclasses regardless of enabled status.

    :param configuration: The Configuration object to search
    :param segment_id: The ID of the segment to search in
    :param class_name: The DAL class name to find
    :returns: List of DAL objects of the specified class
    :rtype: list[DalBase]
    :raises ConfigReadException: If the segment cannot be found
    """
    if not dal_in_config(configuration, "Segment", segment_id):
        return []

    try:
        segment = configuration.get_dal("Segment", segment_id)
    except RuntimeError as e:
        raise ConfigReadException(
            f"Cannot find {segment_id} in {configuration!r}"
        ) from e

    dals_of_class: list[DalBase] = []

    classes_to_check = (*configuration.subclasses(class_name), class_name)

    rels = configuration.relations("Segment", True)
    for rel in rels.keys():
        rel_vals = getattr(segment, rel, [])

        if not isinstance(rel_vals, list):
            rel_vals = [rel_vals]

        dals_of_class.extend(r for r in rel_vals if r.className() in classes_to_check)

    return dals_of_class


def get_class_from_segment_list(
    configuration: Configuration, segment_list: list[str], class_name: str
):
    """Get all instances of a class in a list of segments.

    :param configuration: The Configuration object to search
    :param segment_list: List of segment IDs to search in
    :param class_name: The DAL class name to find
    :returns: List of DAL objects of the specified class
    :rtype: list[DalBase]
    """
    return [
        item
        for seg in segment_list
        for item in get_class_from_segment(configuration, seg, class_name)
    ]


def class_in_config(configuration: Configuration, class_name: str):
    """Check if a class exists in the configuration.

    :param configuration: The Configuration object to check
    :param class_name: The name of the class to check for
    :returns: True if the class exists in the configuration
    :rtype: bool
    """
    return class_name in configuration.classes()


def dal_in_config(configuration: Configuration, class_name: str, dal_id: str):
    """Check if a specific DAL object exists in the configuration.

    :param configuration: The Configuration object to check
    :param class_name: The DAL class name
    :param dal_id: The DAL object ID
    :returns: True if the DAL exists in the configuration
    :rtype: bool
    """
    if not class_in_config(configuration, class_name):
        return False

    return dal_id in [d.id for d in configuration.get_dals(class_name)]


def setup_working_directory(base_path: Path, backup_dir_prefix: str):
    """Setup working directory structure for configuration management.

    Generates a current_config directory and manages backups, keeping only
    the 5 most recent backup directories.

    :param base_path: Base directory path for configuration storage
    :param backup_dir_prefix: Prefix for backup directory names
    :returns: Tuple of (current_config_dir, backup_dir) paths
    :rtype: tuple[Path, Path]
    """
    base_path.mkdir(exist_ok=True, parents=True)

    current_dir = base_path / "current_config"
    if current_dir.exists():
        # Clear it out
        files = sorted(
            (
                f
                for f in base_path.glob("*")
                if f.name != "current_config" and f.is_dir()
            ),
            key=os.path.getmtime,
        )

        if len(files) > 5:
            dirs = files.pop(0)
            shutil.rmtree(dirs)

    current_dir.mkdir(exist_ok=True, parents=True)

    backup_dir = base_path / backup_dir_prefix
    backup_dir.mkdir(parents=True, exist_ok=True)

    return current_dir, backup_dir
