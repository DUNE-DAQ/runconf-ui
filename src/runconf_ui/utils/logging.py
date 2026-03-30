# logger.py
from pathlib import Path
from typing import Literal

from daqpytools.logging import get_daq_logger

from runconf_ui.exceptions import LoggerNotFound

LogLevels = Literal["INFO", "DEBUG", "WARNING"]

_LOGGER_NAME = "runconf_ui_logger"
_logger = None


def init_logger(log_file: Path, log_level: LogLevels = "INFO"):
    """Initialize the global logger for the application.

    Call once at application startup. Creates a DAQ logger with file and stream handlers.
    Subsequent calls are no-ops if logger is already initialized.

    :param log_file: Path to the log file to write to
    :param log_level: Log level (INFO, DEBUG, WARNING)
    """
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
    """Get the global logger instance.

    :returns: The initialized logger instance
    :raises LoggerNotFound: If logger has not been initialized
    """
    if _logger is None:
        raise LoggerNotFound("cannot find logger!")

    return _logger
