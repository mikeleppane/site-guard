"""Logging implementation for site monitoring."""

import json
import os
from pathlib import Path
from typing import Any, Self

from loguru import logger

from site_guard.domain.models.result import SiteCheckResult
from site_guard.domain.services.logger import IoLogger


class FileLogger(IoLogger):
    """Loguru-based file logger for check results with pretty-printed JSON."""

    def __init__(self, log_file_path: str) -> None:
        self._log_file_path = log_file_path
        self._sink_id: int | None = None

    async def __aenter__(self) -> Self:
        # Add file sink with a filter to only log our specific messages
        self._sink_id = logger.add(
            self._log_file_path,
            format="{message}",
            level="INFO",
            rotation="50 MB",
            retention="14 days",
            compression="gz",
            serialize=False,
            filter=lambda record: record.get("extra", {}).get("file_only", False),
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._sink_id is not None:
            logger.remove(self._sink_id)

    async def log_result(self, result: SiteCheckResult) -> None:
        """Log a check result to file with pretty-printed JSON."""
        if self._sink_id is None:
            raise RuntimeError("Logger not initialized. Use as async context manager.")

        log_entry = {
            "timestamp": result.timestamp.isoformat(),
            "url": str(result.url),
            "status": result.status.value,
            "response_time_ms": result.response_time_ms,
            "error_message": result.error_message,
            "failed_content_requirements": result.failed_content_requirements,
            "check_type": "site_monitoring",
        }

        pretty_json = json.dumps(log_entry, indent=2, ensure_ascii=False, sort_keys=True)

        # Write directly to file without using loguru's logging system
        with Path.open(Path(self._log_file_path), "a", encoding="utf-8") as f:
            f.write(pretty_json + "\n")
            f.flush()
            os.fsync(f.fileno())
