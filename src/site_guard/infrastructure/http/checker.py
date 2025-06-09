"""HTTP client implementation for site checking."""

import asyncio
import time
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Self

import aiohttp
from aiohttp import ClientTimeout
from loguru import logger

from site_guard.domain.models.config import RetryConfig, SiteConfig
from site_guard.domain.models.content import ContentRequirement
from site_guard.domain.models.result import SiteCheckResult
from site_guard.domain.models.status import CheckStatus
from site_guard.domain.services.checker import SiteChecker


class RetryableHttpError(Exception):
    """Exception for HTTP errors that should be retried."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


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
        """Check a site with retry mechanism."""

        if not self._session:
            raise RuntimeError("Session not initialized. Use with_session() context manager.")

        retry_config = site_config.retry_config
        last_exception = None

        for attempt in range(retry_config.max_attempts):
            try:
                # Log retry attempt
                if attempt > 0:
                    logger.info(
                        f"Retry attempt {attempt + 1}/{retry_config.max_attempts} for {site_config.url}"
                    )

                # Perform the actual check
                result = await self._perform_single_check(site_config)

                # Check if we should retry based on result
                if (
                    self._should_retry(result, retry_config, attempt)
                    and attempt < retry_config.max_attempts - 1
                ):
                    delay = retry_config.calculate_delay(attempt + 1)
                    logger.warning(
                        f"Retrying {site_config.url} in {delay:.2f}s due to status {result.status.value}"
                    )
                    await asyncio.sleep(delay)
                    continue

                # Success or final attempt
                if attempt > 0:
                    logger.info(
                        f"Successfully checked {site_config.url} after {attempt + 1} attempts"
                    )

                return result

            except (aiohttp.ClientError, TimeoutError, RetryableHttpError) as e:
                last_exception = e

                # Check if we should retry this exception
                if (
                    self._should_retry_exception(e, retry_config, attempt)
                    and attempt < retry_config.max_attempts - 1
                ):
                    delay = retry_config.calculate_delay(attempt + 1)
                    logger.warning(
                        f"Retrying {site_config.url} in {delay:.2f}s due to error: {type(e).__name__}: {e}"
                    )
                    await asyncio.sleep(delay)
                    continue

                # Final attempt or non-retryable error
                break

        # All retries exhausted or non-retryable error
        logger.error(
            f"All {retry_config.max_attempts} attempts failed for {site_config.url}. "
            f"Last error: {type(last_exception).__name__}: {last_exception}"
        )

        return self._create_error_result(site_config, last_exception, retry_config.max_attempts)

    async def _perform_single_check(self, site_config: SiteConfig) -> SiteCheckResult:
        """Perform a single check attempt."""

        start_time = time.perf_counter()

        try:
            # Prepare request parameters
            timeout = aiohttp.ClientTimeout(total=site_config.timeout)

            # Perform HTTP request
            async with self._session.get(  # type: ignore[union-attr]
                str(site_config.url),
                timeout=timeout,
            ) as response:
                end_time = time.perf_counter()
                response_time_ms = int((end_time - start_time) * 1000)

                # Read response content
                content = await response.text()

                # Check for HTTP error status codes
                if response.status >= 400:
                    raise RetryableHttpError(
                        status_code=response.status,
                        message=f"HTTP error {response.status}: {response.reason}",
                    )

                # Perform content checks
                content_check_passed = self._check_content_requirements(
                    content, site_config.content_requirements, site_config.require_all_content
                )

                # Determine overall status
                if content_check_passed:
                    status = CheckStatus.SUCCESS
                    error_message = None
                else:
                    status = CheckStatus.CONTENT_ERROR
                    error_message = "Content requirements not met"

                return SiteCheckResult(
                    url=site_config.url,
                    timestamp=start_time,
                    status=status,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    http_status_code=response.status,
                    content_check_passed=content_check_passed,
                )

        except TimeoutError:
            end_time = time.perf_counter()
            response_time_ms = int((end_time - start_time) * 1000)

            return SiteCheckResult(
                url=site_config.url,
                timestamp=start_time,
                status=CheckStatus.TIMEOUT_ERROR,
                response_time_ms=response_time_ms,
                error_message=f"Request timed out after {site_config.timeout} seconds",
            )

        except aiohttp.ClientConnectorError as e:
            end_time = time.perf_counter()
            response_time_ms = int((end_time - start_time) * 1000)

            return SiteCheckResult(
                url=site_config.url,
                timestamp=start_time,
                status=CheckStatus.CONNECTION_ERROR,
                response_time_ms=response_time_ms,
                error_message=f"Connection error: {e!s}",
            )

    def _should_retry(
        self, result: SiteCheckResult, retry_config: RetryConfig, attempt: int
    ) -> bool:
        """Determine if we should retry based on the result."""

        if not retry_config.enabled or attempt >= retry_config.max_attempts - 1:
            return False

        # Retry on specific status codes
        if result.status == CheckStatus.SERVER_ERROR:
            return True

        # Retry on timeout if configured
        if retry_config.retry_on_timeout and result.status == CheckStatus.TIMEOUT_ERROR:
            return True

        # Retry on connection errors if configured
        return bool(
            retry_config.retry_on_connection_error and result.status == CheckStatus.CONNECTION_ERROR
        )

    def _should_retry_exception(
        self, exception: Exception, retry_config: RetryConfig, attempt: int
    ) -> bool:
        """Determine if we should retry based on the exception."""

        if not retry_config.enabled or attempt >= retry_config.max_attempts - 1:
            return False

        # Retry on retryable HTTP errors
        if isinstance(exception, RetryableHttpError):
            return exception.status_code in retry_config.retry_on_status_codes

        # Retry on timeout errors if configured
        if isinstance(exception, asyncio.TimeoutError) and retry_config.retry_on_timeout:
            return True

        # Retry on connection errors if configured
        if (
            isinstance(exception, aiohttp.ClientConnectorError)
            and retry_config.retry_on_connection_error
        ):
            return True

        # Retry on other client errors if configured
        return bool(
            isinstance(exception, aiohttp.ClientError) and retry_config.retry_on_connection_error
        )

    def _create_error_result(
        self, site_config: SiteConfig, exception: Exception | None, attempts: int
    ) -> SiteCheckResult:
        """Create an error result after all retry attempts failed."""

        if isinstance(exception, RetryableHttpError):
            status = CheckStatus.CONNECTION_ERROR
            error_message = (
                f"HTTP {exception.status_code} after {attempts} attempts: {exception.message}"
            )
            http_status_code = exception.status_code
        elif isinstance(exception, asyncio.TimeoutError):
            status = CheckStatus.TIMEOUT_ERROR
            error_message = f"Timeout after {attempts} attempts"
            http_status_code = None
        elif isinstance(exception, aiohttp.ClientConnectorError):
            status = CheckStatus.CONNECTION_ERROR
            error_message = f"Connection error after {attempts} attempts: {exception!s}"
            http_status_code = None
        else:
            status = CheckStatus.CONNECTION_ERROR
            error_message = f"Unknown error after {attempts} attempts: {exception!s}"
            http_status_code = None

        return SiteCheckResult(
            url=site_config.url,
            timestamp=datetime.now(UTC),
            status=status,
            response_time_ms=0,
            error_message=error_message,
            http_status_code=http_status_code,
        )

    def _check_content_requirements(
        self, content: str, requirements: Sequence[ContentRequirement | str], require_all: bool
    ) -> bool:
        """Check if content meets the specified requirements."""

        if not requirements:
            return True

        if require_all:
            # All requirements must match
            return all(
                req.matches(content) if isinstance(req, ContentRequirement) else req in content
                for req in requirements
            )
        return any(
            req.matches(content) if isinstance(req, ContentRequirement) else req in content
            for req in requirements
        )
