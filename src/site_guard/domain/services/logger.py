from abc import ABC, abstractmethod
from typing import Any

from site_guard.domain.models.result import SiteCheckResult


class IoLogger(ABC):
    """Abstract service for logging check results."""

    @abstractmethod
    async def log_result(self, result: SiteCheckResult) -> None:
        """Log a single check result."""

    @abstractmethod
    async def __aenter__(self) -> "IoLogger":
        """Enter context manager for logging."""

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Exit context manager for logging."""
