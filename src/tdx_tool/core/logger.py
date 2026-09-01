# Dependencies
from logging import getLogger, NullHandler, Logger

LOGGER_NAME = "tdx_tool"

def get_logger(name: str | None = None) -> Logger:
    """
    Get a logger instance with a NullHandler to avoid "No handler found" warnings.

    Parameters
    ----------
    name: str, default: "tdx_tool"
        The name of the logger. If None, the root logger is returned.

    Returns
    -------
    Logger
        A logger instance with a NullHandler.
    """
    if name is None:
        return getLogger(LOGGER_NAME)

    if not name.startswith(LOGGER_NAME):
        name = f"{LOGGER_NAME}.{name}"

    return getLogger(name)

_root_logger = get_logger(LOGGER_NAME)
_root_logger.addHandler(NullHandler())