"""Application service for site monitoring."""

import asyncio

from loguru import logger

from site_guard.domain.models.config import MonitoringConfig
from site_guard.domain.services.checker import SiteChecker
from site_guard.domain.services.logger import IoLogger
from site_guard.domain.services.monitoring import MonitoringService
from site_guard.infrastructure.http.checker import HttpSiteChecker

app_logger = logger


class MonitoringApplication:
    """Main application service for site monitoring."""

    def __init__(
        self, config: MonitoringConfig, site_checker: SiteChecker, io_logger: IoLogger
    ) -> None:
        self._config = config
        self._site_checker = site_checker
        self._running = False
        self._logger = io_logger

    async def run(
        self,
        check_interval: int | None = None,
    ) -> None:
        """Run the monitoring application."""

        # Override check interval if provided
        if check_interval is not None:
            self._config = self._config.with_overridden_interval(check_interval)

        # Override log file if provided via CLI

        app_logger.info(f"Starting site monitoring with {len(self._config.sites)} sites")
        app_logger.info(f"Check interval: {self._config.check_interval} seconds")

        async with (
            HttpSiteChecker().with_session() as site_checker,
            self._logger as output_logger,
        ):
            monitoring_service = MonitoringService(site_checker, output_logger)

            self._running = True
            try:
                while self._running:
                    app_logger.info("Starting monitoring round...")

                    success_count = 0
                    error_count = 0

                    async for result in monitoring_service.monitor_sites(self._config.sites):
                        if result.is_success:
                            success_count += 1
                            app_logger.info(
                                f"\033[32mPASS ✓\033[0m: {result.url} - {result.response_time_ms}ms",
                                flush=True,
                            )
                        else:
                            error_count += 1
                            app_logger.warning(
                                f"\033[31mFAIL ✗\033[0m: {result.url} - {result.status.value}: {result.error_message}"
                            )  # Ensure a newline after the last result
                    app_logger.info(
                        f"Monitoring round completed: {success_count} successful, {error_count} failed"
                    )

                    await asyncio.sleep(self._config.check_interval)

            except KeyboardInterrupt:
                app_logger.info("Monitoring stopped by user")
                self._running = False

    def stop(self) -> None:
        """Stop the monitoring application."""
        self._running = False
