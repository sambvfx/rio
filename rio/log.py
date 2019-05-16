import os
import logging


__all__ = (
    'get_logger',
)


logging.basicConfig()


_LOGGING_LOOKUP = {
    'CRITICAL': logging.CRITICAL,
    'FATAL': logging.FATAL,
    'ERROR': logging.ERROR,
    'WARN': logging.WARNING,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET,
}


_LOGGING_LEVEL = _LOGGING_LOOKUP.get(
    os.environ.get('RIO_LOG_LEVEL', 'INFO'), logging.INFO)


def get_logger(name):
    """
    Helper to get a logger that is configured at a top-level.

    Parameters
    ----------
    name : str

    Returns
    -------
    logging.Logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(_LOGGING_LEVEL)
    return logger
