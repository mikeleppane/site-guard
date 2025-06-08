import asyncio
from collections.abc import AsyncIterator, Iterable

from loguru import logger

from site_guard.domain.models.config import SiteConfig
from site_guard.domain.models.result import SiteCheckResult
from site_guard.domain.services.checker import SiteChecker
from site_guard.domain.services.logger import IoLogger


class MonitoringService:
    """Service for coordinating site monitoring."""

    def __init__(self, site_checker: SiteChecker, logger: IoLogger) -> None:
        self._site_checker = site_checker
        self._logger = logger

    async def monitor_sites(  # noqa: RUF100, C901
        self, sites: Iterable[SiteConfig]
    ) -> AsyncIterator[SiteCheckResult]:
        """Monitor multiple sites and yield results."""

        sites_list = list(sites)

        if not sites_list:
            return

        # Create all tasks
        tasks = [asyncio.create_task(self._site_checker.check_site(site)) for site in sites_list]
        try:
            # Use as_completed to yield results as they finish
            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                    await self._logger.log_result(result)
                    yield result
                except Exception as e:
                    logger.error(f"Site check failed: {type(e).__name__}: {e}")
                    # Continue with other sites even if one fails
                    continue

        except asyncio.CancelledError:
            # Cancel all remaining tasks
            logger.info("Site monitoring cancelled, cleaning up tasks...")
            for task in tasks:
                if not task.done():
                    task.cancel()

            # Wait for cancellation to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

        except Exception as e:
            logger.error(f"Unexpected error in monitor_sites: {type(e).__name__}: {e}")
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
