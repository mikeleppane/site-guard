import asyncio
import tempfile
from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
import yaml
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from pydantic import HttpUrl

from site_guard.domain.models.config import MonitoringConfig, SiteConfig
from site_guard.domain.models.content import ContentRequirement
from site_guard.domain.models.result import SiteCheckResult
from site_guard.domain.models.status import CheckStatus
from site_guard.domain.services.monitoring import MonitoringService


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
async def mock_web_server(aiohttp_client: TestClient) -> AsyncGenerator[TestClient]:
    """Create a mock web server for testing."""

    async def success_handler(request: Any) -> web.Response:
        """Handler that returns successful content."""
        return web.Response(
            text="<html><body>Welcome to Python programming site</body></html>",
            content_type="text/html",
        )

    async def error_handler(request: Any) -> web.Response:
        """Handler that returns 404 error."""
        return web.Response(status=404, text="Not Found")

    async def slow_handler(request: Any) -> web.Response:
        """Handler that simulates slow response."""
        await asyncio.sleep(2)
        return web.Response(text="Slow response with Python content")

    async def missing_content_handler(request: Any) -> web.Response:
        """Handler that returns content without required patterns."""
        return web.Response(
            text="<html><body>This is a Java programming site</body></html>",
            content_type="text/html",
        )

    app = web.Application()
    app.router.add_get("/success", success_handler)
    app.router.add_get("/error", error_handler)
    app.router.add_get("/slow", slow_handler)
    app.router.add_get("/missing-content", missing_content_handler)

    return await aiohttp_client(app)  # type: ignore[no-any-return]


@pytest.fixture
def temp_config_file() -> Generator[Path]:
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


@pytest.fixture
async def test_server() -> AsyncGenerator[TestClient]:
    """Create a test HTTP server with client."""

    async def success_handler(request: Any) -> web.Response:
        """Handler that returns successful content."""
        return web.Response(
            text="<html><body>Welcome to Python programming site</body></html>",
            content_type="text/html",
        )

    async def error_handler(request: Any) -> web.Response:
        """Handler that returns 404 error."""
        return web.Response(status=404, text="Not Found")

    async def slow_handler(request: Any) -> web.Response:
        """Handler that simulates slow response."""
        await asyncio.sleep(2)
        return web.Response(text="Slow response with Python content")

    async def missing_content_handler(request: Any) -> web.Response:
        """Handler that returns content without required patterns."""
        return web.Response(
            text="<html><body>This is a Java programming site</body></html>",
            content_type="text/html",
        )

    async def delay_handler(request: Any) -> web.Response:
        """Handler with configurable delay."""
        delay = float(request.query.get("delay", 0))
        await asyncio.sleep(delay)
        return web.Response(text=f"Python response after {delay}s delay")

    # Create the web application
    app = web.Application()
    app.router.add_get("/success", success_handler)
    app.router.add_get("/error", error_handler)
    app.router.add_get("/slow", slow_handler)
    app.router.add_get("/missing-content", missing_content_handler)
    app.router.add_get("/delay", delay_handler)

    # Create test server and client
    server = TestServer(app, port=8080)
    client = TestClient(server, loop=asyncio.get_event_loop())

    try:
        # Start the server
        await server.start_server()
        yield client
    finally:
        # Cleanup
        await client.close()
        await server.close()
