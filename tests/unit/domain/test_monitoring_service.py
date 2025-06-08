from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from pydantic import HttpUrl

from site_guard.domain.models.config import SiteConfig
from site_guard.domain.models.result import SiteCheckResult
from site_guard.domain.models.status import CheckStatus
from site_guard.domain.services.monitoring import MonitoringService


@pytest.mark.asyncio
async def test_monitor_sites_success(
    monitoring_service: MonitoringService,
    mock_site_checker: AsyncMock,
    sample_sites: list[SiteConfig],
    mock_logger: AsyncMock,
) -> None:
    """Test successful monitoring of multiple sites."""
    # Setup mock responses
    mock_results = [
        SiteCheckResult(
            url=HttpUrl("https://example.com"),
            status=CheckStatus.SUCCESS,
            response_time_ms=200,
            timestamp=datetime.now(),
        ),
        SiteCheckResult(
            url=HttpUrl("https://test.com"),
            status=CheckStatus.SUCCESS,
            response_time_ms=150,
            timestamp=datetime.now(),
        ),
    ]

    mock_site_checker.check_site.side_effect = mock_results

    # Execute monitoring
    results = [result async for result in monitoring_service.monitor_sites(sample_sites)]

    # Verify results
    assert len(results) == 2
    assert all(r.status == CheckStatus.SUCCESS for r in results)

    # Verify checker was called for each site
    assert mock_site_checker.check_site.call_count == 2

    # Verify logger was called for each result
    assert mock_logger.log_result.call_count == 2


@pytest.mark.asyncio
async def test_monitor_sites_with_failures(
    monitoring_service: MonitoringService,
    mock_site_checker: AsyncMock,
    sample_sites: list[SiteConfig],
) -> None:
    """Test monitoring with some failures."""
    mock_results = [
        SiteCheckResult(
            url=HttpUrl("https://example.com"),
            status=CheckStatus.SUCCESS,
            response_time_ms=200,
            timestamp=datetime.now(),
        ),
        SiteCheckResult(
            url=HttpUrl("https://test.com"),
            status=CheckStatus.CONNECTION_ERROR,
            response_time_ms=None,
            timestamp=datetime.now(),
            error_message="Connection failed",
        ),
    ]

    mock_site_checker.check_site.side_effect = mock_results

    results = [result async for result in monitoring_service.monitor_sites(sample_sites)]

    assert len(results) == 2
    assert results[0].status == CheckStatus.SUCCESS
    assert results[1].status == CheckStatus.CONNECTION_ERROR
