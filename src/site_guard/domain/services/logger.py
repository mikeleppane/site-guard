from abc import ABC, abstractmethod

from site_guard.domain.models.result import SiteCheckResult


class IoLogger(ABC):
    """Abstract service for logging check results."""

    @abstractmethod
    async def log_result(self, result: SiteCheckResult) -> None:
        """Log a single check result."""
