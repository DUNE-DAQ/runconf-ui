import logging
import os
import shutil
from pathlib import Path
from typing import Union


def clean_old_files(
    logging_path: Path,
    extension: str = "log",
    n_files: int = 5,
    include_folders: bool = False,
    folder_prefix: str = "",
) -> None:
    """
    Check if the logging directory has more than `n_files` files or folders and delete the oldest ones if it does.

    Args:
        logging_path (Path): The directory to clean.
        extension (str): The file extension to look for (default: "log").
        n_files (int): The maximum number of files or folders to keep (default: 5).
        include_folders (bool): Whether to include folders in the cleanup (default: False).
        folder_prefix (str): Prefix to filter folders (default: "").
    """
    # Clean up old files
    files = sorted(logging_path.glob(f"*.{extension}"), key=os.path.getmtime)
    while len(files) > n_files:
        oldest_file = files.pop(0)
        os.remove(oldest_file)
        logging.info(f"Deleted old file: {oldest_file}")

    # Clean up old folders if enabled
    if include_folders:
        folders = sorted(
            [f for f in logging_path.iterdir() if f.is_dir() and f.name.startswith(folder_prefix)],
            key=os.path.getmtime,
        )
                
        while len(folders) > n_files:
            oldest_folder = folders.pop(0)
            shutil.rmtree(oldest_folder) if oldest_folder.is_dir() else os.remove(oldest_folder)
            logging.info(f"Deleted old folder: {oldest_folder}")