"""HTTP client implementation for site checking."""

import time
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Self

import aiohttp
from aiohttp import ClientTimeout

from site_guard.domain.models.config import SiteConfig
from site_guard.domain.models.result import SiteCheckResult
from site_guard.domain.models.status import CheckStatus
from site_guard.domain.services.checker import SiteChecker


class HttpSiteChecker(SiteChecker):
    """HTTP-based implementation of site checking."""

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        self._session = session
        self._owned_session = session is None

    @asynccontextmanager
    async def with_session(self) -> AsyncIterator[Self]:
        """Async context manager for HTTP session."""
        if self._session is None:
            timeout = ClientTimeout(total=60)
            self._session = aiohttp.ClientSession(timeout=timeout)
            try:
                yield self
            finally:
                if self._owned_session and self._session:
                    await self._session.close()
        else:
            yield self

    async def check_site(self, site_config: SiteConfig) -> SiteCheckResult:
        """Check a single site."""
        start_time = time.perf_counter()
        timestamp = datetime.now()

        if not self._session:
            raise RuntimeError("HTTP session not initialized. Use as async context manager.")

        try:
            timeout = ClientTimeout(total=site_config.timeout)
            async with self._session.get(str(site_config.url), timeout=timeout) as response:
                end_time = time.perf_counter()
                response_time_ms = int((end_time - start_time) * 1000)

                # Check HTTP status
                if response.status >= 400:
                    return SiteCheckResult(
                        url=site_config.url,
                        status=CheckStatus.CONNECTION_ERROR,
                        response_time_ms=response_time_ms,
                        timestamp=timestamp,
                        error_message=f"HTTP {response.status}: {response.reason}",
                    )

                # Check content requirements
                content = await response.text()
                site_result = site_config.check_content_requirements(content)

                if not site_result.success:
                    error_msg = self._build_content_error_message(
                        site_result.failed_patterns, site_config.require_all_content
                    )
                    return SiteCheckResult(
                        url=site_config.url,
                        status=CheckStatus.CONTENT_ERROR,
                        response_time_ms=response_time_ms,
                        timestamp=timestamp,
                        error_message=error_msg,
                        failed_content_requirements=site_result.failed_patterns,
                    )

                return SiteCheckResult(
                    url=site_config.url,
                    status=CheckStatus.SUCCESS,
                    response_time_ms=response_time_ms,
                    timestamp=timestamp,
                )

        except TimeoutError:
            end_time = time.perf_counter()
            response_time_ms = int((end_time - start_time) * 1000)
            return SiteCheckResult(
                url=site_config.url,
                status=CheckStatus.TIMEOUT_ERROR,
                response_time_ms=response_time_ms,
                timestamp=timestamp,
                error_message=f"Request timeout after {site_config.timeout}s",
            )

        except Exception as e:
            end_time = time.perf_counter()
            response_time_ms = int((end_time - start_time) * 1000)
            return SiteCheckResult(
                url=site_config.url,
                status=CheckStatus.CONNECTION_ERROR,
                response_time_ms=response_time_ms,
                timestamp=timestamp,
                error_message=f"Connection error: {e!s}",
            )

    def _build_content_error_message(
        self, failed_patterns: Sequence[str], require_all: bool
    ) -> str:
        """Build a descriptive error message for content validation failures."""
        if require_all:
            return f"Content requirements not met. Failed patterns: {', '.join(failed_patterns)}"
        return f"No content requirements matched. Failed patterns: {', '.join(failed_patterns)}"
