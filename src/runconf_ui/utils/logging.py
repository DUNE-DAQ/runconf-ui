# logger.py
from pathlib import Path
from typing import Literal

from daqpytools.logging import get_daq_logger

from runconf_ui.exceptions import LoggerNotFound

LogLevels = Literal["INFO", "DEBUG", "WARNING"]

_LOGGER_NAME = "runconf_ui_logger"
_LOGGER = None

def init_logger(log_file: Path, log_level: LogLevels = "INFO"):
    global _LOGGER
    if _LOGGER is not None:
        return

    log_file.parent.mkdir(parents=True, exist_ok=True)
    _LOGGER = get_daq_logger(
        logger_name=_LOGGER_NAME,
        log_level=log_level,
        use_parent_handlers=False,  # was True
        rich_handler=False,
        stream_handlers=False,
        file_handler_path=str(log_file),
    )
    _LOGGER.propagate = False  # belt-and-braces


def get_logger():
    if _LOGGER is None:
        raise LoggerNotFound("cannot find logger!")

    return _LOGGER
