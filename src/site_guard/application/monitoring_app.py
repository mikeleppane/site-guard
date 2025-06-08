"""Application service for site monitoring."""

import asyncio
import time
from dataclasses import dataclass

from loguru import logger

from site_guard.domain.models.config import MonitoringConfig
from site_guard.domain.models.result import SiteCheckResult
from site_guard.domain.services.checker import SiteChecker
from site_guard.domain.services.logger import IoLogger
from site_guard.domain.services.monitoring import MonitoringService
from site_guard.infrastructure.http.checker import HttpSiteChecker

app_logger = logger


@dataclass
class MonitoringRoundResult:
    """Result of a single monitoring round."""

    success_count: int
    error_count: int
    duration_seconds: float

    @property
    def total_checks(self) -> int:
        return self.success_count + self.error_count


class MonitoringApplication:
    """Main application service for site monitoring."""

    def __init__(
        self, config: MonitoringConfig, site_checker: SiteChecker, io_logger: IoLogger
    ) -> None:
        self._config = config
        self._site_checker = site_checker
        self._running = False
        self._logger = io_logger

    async def run(self, check_interval: int | None = None) -> None:
        """Run the monitoring application."""
        try:
            # Apply configuration overrides
            effective_config = self._prepare_configuration(check_interval)

            # Log startup information
            self._log_startup_info(effective_config)

            # Run monitoring loop
            await self._run_monitoring_loop(effective_config)

        except KeyboardInterrupt:
            app_logger.info("Monitoring stopped by user")
        finally:
            self._running = False

    def stop(self) -> None:
        """Stop the monitoring application."""
        self._running = False

    def _prepare_configuration(self, check_interval: int | None) -> MonitoringConfig:
        """Prepare the effective configuration with any overrides."""

        if check_interval is not None:
            return self._config.with_overridden_interval(check_interval)

        return self._config

    def _log_startup_info(self, config: MonitoringConfig) -> None:
        """Log application startup information."""
        app_logger.info(f"Starting site monitoring with {len(config.sites)} sites")
        app_logger.info(f"Check interval: {config.check_interval} seconds")

        for site in config.sites:
            app_logger.debug(f"Monitoring site: {site.url}")

    async def _run_monitoring_loop(self, config: MonitoringConfig) -> None:
        """Run the main monitoring loop."""
        async with HttpSiteChecker().with_session() as site_checker, self._logger as output_logger:
            monitoring_service = MonitoringService(site_checker, output_logger)

            self._running = True
            round_number = 1

            while self._running:
                try:
                    round_result = await self._execute_monitoring_round(
                        monitoring_service, config, round_number
                    )

                    self._log_round_completion(round_result, round_number)

                    if self._running:  # Check if still running before sleeping
                        await asyncio.sleep(config.check_interval)

                    round_number += 1

                except Exception as e:
                    app_logger.error(f"Error in monitoring round {round_number}: {e}")
                    await asyncio.sleep(5)  # Brief pause before retrying

    async def _execute_monitoring_round(
        self, monitoring_service: MonitoringService, config: MonitoringConfig, round_number: int
    ) -> MonitoringRoundResult:
        """Execute a single monitoring round and return results."""
        app_logger.info(f"Starting monitoring round #{round_number}...")

        start_time = time.perf_counter()
        success_count = 0
        error_count = 0

        async for result in monitoring_service.monitor_sites(config.sites):
            if result.is_success:
                success_count += 1
                self._log_success_result(result)
            else:
                error_count += 1
                self._log_failure_result(result)

        end_time = time.perf_counter()
        duration = end_time - start_time

        return MonitoringRoundResult(
            success_count=success_count, error_count=error_count, duration_seconds=duration
        )

    def _log_success_result(self, result: SiteCheckResult) -> None:
        """Log a successful monitoring result."""
        app_logger.info(f"\033[32mPASS ✓\033[0m: {result.url} - {result.response_time_ms}ms")

    def _log_failure_result(self, result: SiteCheckResult) -> None:
        """Log a failed monitoring result."""
        app_logger.warning(
            f"\033[31mFAIL ✗\033[0m: {result.url} - {result.status.value}: {result.error_message}"
        )

    def _log_round_completion(self, result: MonitoringRoundResult, round_number: int) -> None:
        """Log the completion of a monitoring round."""
        app_logger.info(
            f"Round #{round_number} completed in {result.duration_seconds:.2f}s: "
            f"{result.success_count} successful, {result.error_count} failed"
        )
