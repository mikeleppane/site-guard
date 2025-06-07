"""Logging setup and configuration."""

import sys

from loguru import logger


def setup_console_logging(verbose: bool = False) -> None:
    """Setup console logging with loguru."""
    # Remove default handler
    logger.remove()

    # Console handler with colored output
    log_level = "DEBUG" if verbose else "INFO"

    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )


def setup_file_logging(log_file: str) -> None:
    """Setup file logging with rotation."""
    logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="5 MB",
        retention="7 days",
    )


def setup_logging(verbose: bool = False, log_file: str | None = None) -> None:
    """Setup complete logging configuration."""
    setup_console_logging(verbose)

    if log_file:
        setup_file_logging(log_file)
