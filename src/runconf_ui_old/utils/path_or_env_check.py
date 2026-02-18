import os
from pathlib import Path


def path_or_env_check(var_str: str):
    if os.getenv(var_str):
        return os.getenv(var_str)

    var_str_path = Path(var_str)
    if var_str_path.exists():
        return var_str_path

    # If the path doesn't exist, return the original string
    return var_str
