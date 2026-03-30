"""Utility functions for safely handling OKS configurations."""

import os
import shutil
from pathlib import Path

from conffwk import Configuration
from conffwk.dal import DalBase
from daqconf.consolidate import consolidate_files

from runconf_ui.exceptions import ConfigReadException


def open_configuration(config_path: Path) -> Configuration:
    """Open and return an OKS configuration from the given path."""
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
    buffer_file.parent.mkdir(parents=True, exist_ok=True)
    consolidate_files(str(buffer_file), str(original_config))
    return open_configuration(buffer_file)


def get_number_of_sessions(configuration: Configuration) -> int:
    """Return the number of Session DALs in the given configuration."""
    return len(configuration.get_dals("Session"))


def check_config_has_session(config_path: Path) -> bool:
    """Return True if the configuration at the given path contains at least one Session."""
    try:
        conf = open_configuration(config_path)
    except (FileNotFoundError, ConfigReadException):
        return False

    has_session = get_number_of_sessions(conf) > 0
    conf.unload()
    return has_session


def get_config_paths(config_directory: Path):
    if not config_directory.is_dir():
        raise ValueError("Input must be a directory")

    return [f for f in config_directory.rglob("*.data.xml") if f.is_file()]


def get_configs_with_session(config_paths: list[Path] | Path) -> list[Path]:
    """
    Return all configuration files that contain at least one Session.

    Accepts a single file or directory, or a mixed list of both.
    Recursively searches directories for `*.data.xml` files.
    """
    if isinstance(config_paths, Path):
        config_paths = [config_paths]

    config_files: list[Path] = []

    for path in config_paths:
        if path.is_file() and path.name.endswith(".data.xml"):
            config_files.append(path)
        elif path.is_dir():
            config_files += get_config_paths(path)

    return [c for c in config_files if check_config_has_session(c)]


def get_class_from_segment(
    configuration: Configuration, segment_id: str, class_name: str
):
    """
    Find all instances of a class in a segment. This includes all subclasses  (regardless of enabled status)
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
    """
    Get all instances of a class in a list of segments (regardless of enabled status)
    """
    return [
        item
        for seg in segment_list
        for item in get_class_from_segment(configuration, seg, class_name)
    ]


def class_in_config(configuration: Configuration, class_name: str):
    return class_name in configuration.classes()


def dal_in_config(configuration: Configuration, class_name: str, dal_id: str):
    if not class_in_config(configuration, class_name):
        return False

    return dal_id in [d.id for d in configuration.get_dals(class_name)]


def setup_working_directory(base_path: Path, backup_dir_prefix: str):
    """
    Generates a config directory and checks for sub-directories
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
