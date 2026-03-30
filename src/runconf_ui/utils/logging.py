# logger.py
from pathlib import Path
from typing import Literal

from daqpytools.logging import get_daq_logger

from runconf_ui.exceptions import LoggerNotFound

LogLevels = Literal["INFO", "DEBUG", "WARNING"]

_LOGGER_NAME = "runconf_ui_logger"
_logger = None


def init_logger(log_file: Path, log_level: LogLevels = "INFO"):
    """Call once at application startup."""
    global _logger
    if _logger is not None:
        return

    log_file.parent.mkdir(parents=True, exist_ok=True)
    _logger = get_daq_logger(
        logger_name=_LOGGER_NAME,
        log_level=log_level,
        use_parent_handlers=True,
        rich_handler=True,
        stream_handlers=True,
        file_handler_path=str(log_file),
    )


def get_logger():
    if _logger is None:
        raise LoggerNotFound("cannot find logger!")

    return _logger
