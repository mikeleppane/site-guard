"""Logging implementation for site monitoring."""

import json
from pathlib import Path
from typing import Any, Self, TextIO

from loguru import logger

from site_guard.domain.models.result import SiteCheckResult
from site_guard.domain.services.logger import Logger


class FileLogger(Logger):
    """File-based logger for check results."""

    def __init__(self, log_file_path: Path) -> None:
        self._log_file_path = log_file_path
        self._log_file: TextIO | None = None

    async def __aenter__(self) -> Self:
        self._log_file = Path.open(self._log_file_path, "a", encoding="utf-8")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._log_file:
            self._log_file.close()

    async def log_result(self, result: SiteCheckResult) -> None:
        """Log a check result to file."""
        if not self._log_file:
            raise RuntimeError("Logger not initialized. Use as async context manager.")

        log_entry = {
            "timestamp": result.timestamp.isoformat(),
            "url": result.url,
            "status": result.status.value,
            "response_time_ms": result.response_time_ms,
            "error_message": result.error_message,
        }

        self._log_file.write(json.dumps(log_entry) + "\n")
        self._log_file.flush()


class SiteCheckResultLogger(Logger):
    """Loguru-based logger for check results."""

    def __init__(self, log_file_path: Path) -> None:
        self._log_file_path = log_file_path
        self._sink_id: int | None = None

    async def __aenter__(self) -> Self:
        # Add a structured JSON sink for monitoring results
        self._sink_id = logger.add(
            self._log_file_path,
            format="{message}",
            level="INFO",
            serialize=True,  # Output as JSON
            rotation="10 MB",
            retention="30 days",
            compression="gz",
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._sink_id is not None:
            logger.remove(self._sink_id)

    async def log_result(self, result: SiteCheckResult) -> None:
        """Log a check result using loguru."""
        extra_data = {
            "url": result.url,
            "status": result.status.value,
            "response_time_ms": result.response_time_ms,
            "error_message": result.error_message,
            "timestamp": result.timestamp.isoformat(),
            "check_type": "site_monitoring",
        }

        if result.is_success:
            logger.bind(**extra_data).info(
                f"Site check successful: {result.url} ({result.response_time_ms}ms)"
            )
        else:
            logger.bind(**extra_data).warning(
                f"Site check failed: {result.url} - {result.status.value}: {result.error_message}"
            )
