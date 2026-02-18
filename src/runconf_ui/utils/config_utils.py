"""Utility functions for safely handling OKS configurations."""

from pathlib import Path

from conffwk import Configuration

from runconf_ui.exceptions import ConfigReadException


def open_configuration(config_path: Path) -> Configuration:
    """Open and return an OKS configuration from the given path."""
    if not config_path.name.endswith(".data.xml"):
        raise ConfigReadException(f"{config_path} is not an OKS .data.xml configuration")

    if not config_path.exists():
        raise FileNotFoundError(f"Cannot find {config_path}")

    try:
        return Configuration(f"oksconflibs:{config_path}")
    except Exception as e:
        raise ConfigReadException(f"Cannot open {config_path}") from e

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

def get_class_from_segment(configuration: Configuration, segment_id: str, class_name: str):
    
    segment = configuration.get_dal('Segment', segment_id)
    if segment is None:
        return []
    
    dals_of_class = []
    
    rels = configuration.relations('Segment', True)
    for rel in rels.keys():
        rel_vals = getattr(segment, rel, [])
        
        if not isinstance(rel_vals, list):
            rel_vals = [rel_vals]
        
        dals_of_class.extend(r for r in rel_vals if r.className()==class_name)
    
    return dals_of_class