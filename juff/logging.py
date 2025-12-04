"""Logging configuration for Juff.

This module provides logging setup similar to ruff's verbose output,
with timestamped debug messages and colored output.
"""

import logging
import sys
from datetime import datetime
from enum import Enum
from typing import TextIO


class LogLevel(Enum):
    """Log level configuration for Juff CLI."""

    # Suppress all output except errors
    SILENT = "silent"
    # Suppress non-essential output (warnings and above)
    QUIET = "quiet"
    # Default output level (info and above)
    DEFAULT = "default"
    # Verbose output with debug messages
    VERBOSE = "verbose"

    def to_level_filter(self) -> int:
        """Convert LogLevel to Python logging level."""
        mapping = {
            LogLevel.SILENT: logging.ERROR,
            LogLevel.QUIET: logging.WARNING,
            LogLevel.DEFAULT: logging.INFO,
            LogLevel.VERBOSE: logging.DEBUG,
        }
        return mapping[self]


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and timestamps for verbose output."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def __init__(self, use_colors: bool = True):
        """Initialize the formatter.

        Args:
            use_colors: Whether to use ANSI colors in output.
        """
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with timestamp and optional colors."""
        # Get timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d][%H:%M:%S")

        # Get the logger name (module path)
        name = record.name
        if name.startswith("juff."):
            name = name[5:]  # Remove 'juff.' prefix for cleaner output

        # Build the message
        level = record.levelname

        if self.use_colors:
            color = self.COLORS.get(level, "")
            reset = self.COLORS["RESET"]
            return f"[{timestamp}][{color}{name}{reset}][{level}] {record.getMessage()}"
        else:
            return f"[{timestamp}][{name}][{level}] {record.getMessage()}"


class QuietFormatter(logging.Formatter):
    """Simple formatter for quiet/default mode - just the message."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as just the message."""
        return record.getMessage()


# Global logger instance
_logger: logging.Logger | None = None
_log_level: LogLevel = LogLevel.DEFAULT


def set_up_logging(
    level: LogLevel = LogLevel.DEFAULT,
    stream: TextIO | None = None,
) -> None:
    """Set up logging for Juff.

    Args:
        level: The log level to use.
        stream: Output stream (defaults to stderr).
    """
    global _logger, _log_level
    _log_level = level

    if stream is None:
        stream = sys.stderr

    # Get or create the juff logger
    _logger = logging.getLogger("juff")
    _logger.setLevel(level.to_level_filter())

    # Remove existing handlers
    _logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(stream)
    handler.setLevel(level.to_level_filter())

    # Use colored formatter for verbose, simple for others
    use_colors = hasattr(stream, "isatty") and stream.isatty()

    if level == LogLevel.VERBOSE:
        formatter = ColoredFormatter(use_colors=use_colors)
    else:
        formatter = QuietFormatter()

    handler.setFormatter(formatter)
    _logger.addHandler(handler)

    # Don't propagate to root logger
    _logger.propagate = False


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Optional name for the logger (will be prefixed with 'juff.').

    Returns:
        Logger instance.
    """
    if name:
        return logging.getLogger(f"juff.{name}")
    return logging.getLogger("juff")


def is_verbose() -> bool:
    """Check if verbose logging is enabled."""
    return _log_level == LogLevel.VERBOSE


def is_quiet() -> bool:
    """Check if quiet mode is enabled."""
    return _log_level in (LogLevel.QUIET, LogLevel.SILENT)


def is_silent() -> bool:
    """Check if silent mode is enabled."""
    return _log_level == LogLevel.SILENT


# Convenience functions for logging
def debug(msg: str, *args, logger_name: str | None = None, **kwargs) -> None:
    """Log a debug message."""
    get_logger(logger_name).debug(msg, *args, **kwargs)


def info(msg: str, *args, logger_name: str | None = None, **kwargs) -> None:
    """Log an info message."""
    get_logger(logger_name).info(msg, *args, **kwargs)


def warning(msg: str, *args, logger_name: str | None = None, **kwargs) -> None:
    """Log a warning message."""
    get_logger(logger_name).warning(msg, *args, **kwargs)


def error(msg: str, *args, logger_name: str | None = None, **kwargs) -> None:
    """Log an error message."""
    get_logger(logger_name).error(msg, *args, **kwargs)
