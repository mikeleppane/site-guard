from abc import ABC, abstractmethod

from site_guard.domain.models.config import SiteConfig
from site_guard.domain.models.result import SiteCheckResult


class SiteChecker(ABC):
    """Abstract service for checking individual sites."""

    @abstractmethod
    async def check_site(self, site_config: SiteConfig) -> SiteCheckResult:
        """Check a single site and return the result."""
