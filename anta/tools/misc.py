"""
Toolkit for ANTA.
"""

from __future__ import annotations

import logging
import traceback
from typing import Optional

from anta import __DEBUG__

logger = logging.getLogger(__name__)


def anta_log_exception(exception: Exception, message: Optional[str] = None, calling_logger: Optional[logging.Logger] = None) -> None:
    """
    Helper function to help log exceptions:
    * if anta.__DEBUG__ is True then the logger.exception method is called to get the traceback
    * otherwise logger.error is called

    Args:
        exception (Exception): The Exception being logged
        message (str): An optional message
        calling_logger (logging.Logger): A logger to which the exception should be logged
                                         if not present, the logger in this file is used.

    """
    if calling_logger is None:
        calling_logger = logger
    if __DEBUG__:
        calling_logger.exception(message)
    else:
        calling_logger.error(f"{message} {exc_to_str(exception)}")


def exc_to_str(exception: Exception) -> str:
    """
    Helper function that returns a human readable string from an Exception object
    """
    return f"{type(exception).__name__}{f' ({str(exception)})' if str(exception) else ''}"


def tb_to_str(exception: Exception) -> str:
    """
    Helper function that returns a traceback string from an Exception object
    """
    return "Traceback (most recent call last):\n" + "".join(traceback.format_tb(exception.__traceback__))
