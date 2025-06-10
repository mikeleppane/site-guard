import tempfile
from collections.abc import Generator, Iterator
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import yaml
from pydantic import HttpUrl

from site_guard.domain.models.config import MonitoringConfig, SiteConfig
from site_guard.domain.models.content import ContentRequirement
from site_guard.domain.models.result import SiteCheckResult
from site_guard.domain.models.status import CheckStatus
from site_guard.domain.services.monitoring import MonitoringService
from site_guard.infrastructure.persistence.config import FileConfigLoader


@pytest.fixture
def sample_site_config() -> SiteConfig:
    """Fixture providing a sample site configuration."""
    return SiteConfig(
        url="https://example.com",
        content_requirements=["Welcome", ContentRequirement(pattern="*test*", use_wildcards=True)],
        timeout=30,
        require_all_content=True,
    )


@pytest.fixture
def sample_monitoring_config(sample_site_config: SiteConfig) -> MonitoringConfig:
    """Fixture providing a sample monitoring configuration."""
    return MonitoringConfig(check_interval=60, sites=[sample_site_config], log_file="test.log")


@pytest.fixture
def sample_check_result() -> SiteCheckResult:
    """Fixture providing a sample check result."""
    return SiteCheckResult(
        url=HttpUrl("https://example.com"),
        status=CheckStatus.SUCCESS,
        response_time_ms=200,
        timestamp=datetime.now(),
    )


@pytest.fixture
def temp_config_file() -> Iterator[Path]:
    """Create a temporary configuration file."""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "check_interval": 1,  # Short interval for testing
                "log_file": "test_monitoring.log",
                "sites": [],  # Will be populated in tests
            }
            yaml.dump(config_data, f)
            yield Path(f.name)
    finally:
        Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def temp_log_file() -> Generator[Path]:
    """Create a temporary log file."""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            yield Path(f.name)
    finally:
        # Cleanup
        Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def mock_site_checker() -> AsyncMock:
    """Mock site checker."""
    return AsyncMock()


@pytest.fixture
def mock_logger() -> AsyncMock:
    """Mock logger."""
    return AsyncMock()


@pytest.fixture
def file_config_loader() -> FileConfigLoader:
    """Mock logger."""
    return FileConfigLoader()


@pytest.fixture
def monitoring_service(mock_site_checker: AsyncMock, mock_logger: AsyncMock) -> MonitoringService:
    """Create monitoring service with mocks."""
    return MonitoringService(mock_site_checker, mock_logger)


@pytest.fixture
def sample_sites() -> list[SiteConfig]:
    """Sample site configurations."""
    return [
        SiteConfig(url="https://example.com", content_requirements=["Python"], timeout=10),
        SiteConfig(
            url="https://test.com",
            content_requirements=[ContentRequirement(pattern="*test*", use_wildcards=True)],
            timeout=15,
        ),
    ]
