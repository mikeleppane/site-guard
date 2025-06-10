from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from pydantic import ValidationError

from site_guard.application.monitoring_app import MonitoringApplication
from site_guard.domain.models.result import SiteCheckResult
from site_guard.domain.models.status import CheckStatus
from site_guard.domain.services.monitoring import MonitoringService
from site_guard.infrastructure.http.checker import HttpSiteChecker
from site_guard.infrastructure.logging.logger import FileLogger
from site_guard.infrastructure.persistence.config import FileConfigLoader


@pytest.mark.asyncio
async def test_monitoring_application_should_catch_successful_request(
    temp_config_file: Path, temp_log_file: Generator[Path]
) -> None:
    """Test the complete site monitoring workflow with real HTTP requests.
    TODO: replace actual URLs with test server URLs when available.
    This test will:

    GIVEN: Test data is set up and MonitoringApplication is initialized with a configuration file.
    WHEN: The monitoring application is run
    THEN: It should successfully check the site, log results, and handle content validation.


    """

    config_data = {
        "check_interval": 1,
        "log_file": str(temp_log_file),
        "retry": {"enabled": True, "max_attempts": 3, "delay_seconds": 1, "strategy": "fixed"},
        "sites": [
            {
                "url": "https://httpbin.org/html",
                "content_requirements": ["Herman Melville"],
                "timeout": 5,
                "require_all_content": True,
            },
        ],
    }

    # Write configuration to file

    with temp_config_file.open("w") as f:
        yaml.dump(config_data, f)

    # Create application components
    config_loader = FileConfigLoader()
    config = config_loader.load_config(temp_config_file)
    app_logger = AsyncMock(spec=FileLogger)
    app = MonitoringApplication(config, HttpSiteChecker(), app_logger)

    # Mock the run method to execute monitoring once
    async def mock_run(
        _config_path: Any,
        _check_interval: Any = None,
        _log_file: str | Path | None = None,
        _verbose: bool = False,
    ) -> list[SiteCheckResult]:
        async with HttpSiteChecker().with_session() as site_checker, app_logger as _logger:
            monitoring_service = MonitoringService(site_checker, app_logger)

            return [result async for result in monitoring_service.monitor_sites(config.sites)]

    # Patch and run

    with patch.object(app, "run", side_effect=mock_run):
        results: list[SiteCheckResult] = await app.run(temp_config_file)

    # Verify results
    assert len(results) == 1

    # Check successful site
    success_result = next(r for r in results if "html" in str(r.url))
    assert success_result.status == CheckStatus.SUCCESS
    assert success_result.response_time_ms is not None
    assert success_result.response_time_ms > 0
    assert success_result.error_message is None


@pytest.mark.asyncio
async def test_monitoring_application_should_catch_failed_request(
    temp_config_file: Path, temp_log_file: Generator[Path]
) -> None:
    """Test the complete site monitoring workflow with real HTTP requests.
    This test will:
    GIVEN: Test data is set up and MonitoringApplication is initialized with a configuration file.
    WHEN: The monitoring application is run
    THEN: It should successfully check the site, log results, and handle content validation.

    """

    config_data = {
        "check_interval": 1,
        "log_file": str(temp_log_file),
        "retry": {"enabled": True, "max_attempts": 3, "delay_seconds": 1, "strategy": "fixed"},
        "sites": [
            {
                "url": "https://httpbin.org/status/404",
                "content_requirements": ["Herman Melville"],
                "timeout": 5,
                "require_all_content": True,
            },
        ],
    }

    # Write configuration to file
    with temp_config_file.open("w") as f:
        yaml.dump(config_data, f)

    # Create application components
    config_loader = FileConfigLoader()
    config = config_loader.load_config(temp_config_file)
    app_logger = AsyncMock(spec=FileLogger)
    app = MonitoringApplication(config, HttpSiteChecker(), app_logger)

    # Mock the run method to execute monitoring once
    async def mock_run(
        _config_path: Any,
        _check_interval: Any = None,
        _log_file: str | Path | None = None,
        _verbose: bool = False,
    ) -> list[SiteCheckResult]:
        async with HttpSiteChecker().with_session() as site_checker, app_logger as _logger:
            monitoring_service = MonitoringService(site_checker, app_logger)

            return [result async for result in monitoring_service.monitor_sites(config.sites)]

    # Patch and run
    with patch.object(app, "run", side_effect=mock_run):
        results: list[SiteCheckResult] = await app.run(temp_config_file)

    # Verify results
    assert len(results) == 1

    # Check failed site
    failure_result = next(r for r in results)
    assert failure_result.status == CheckStatus.NOT_FOUND
    assert failure_result.response_time_ms is not None
    assert failure_result.response_time_ms == 0
    assert failure_result.error_message is not None


@pytest.mark.asyncio
async def test_monitoring_application_should_catch_timeout_request(
    temp_config_file: Path, temp_log_file: Generator[Path]
) -> None:
    """Test the complete site monitoring workflow with real HTTP requests.
    This test will:
    GIVEN: Test data is set up and MonitoringApplication is initialized with a configuration file.
    WHEN: The monitoring application is run
    THEN: It should successfully check the site, log results, and handle content validation.

    """

    config_data = {
        "check_interval": 1,
        "log_file": str(temp_log_file),
        "retry": {"enabled": False},
        "sites": [
            {
                "url": "https://httpbin.org/delay/5",
                "content_requirements": ["Herman Melville"],
                "timeout": 1,
                "require_all_content": True,
            },
        ],
    }

    # Write configuration to file
    with temp_config_file.open("w") as f:
        yaml.dump(config_data, f)

    # Create application components
    config_loader = FileConfigLoader()
    config = config_loader.load_config(temp_config_file)
    app_logger = AsyncMock(spec=FileLogger)
    app = MonitoringApplication(config, HttpSiteChecker(), app_logger)

    # Mock the run method to execute monitoring once
    async def mock_run(
        _config_path: Any,
        _check_interval: Any = None,
        _log_file: str | Path | None = None,
        _verbose: bool = False,
    ) -> list[SiteCheckResult]:
        async with HttpSiteChecker().with_session() as site_checker, app_logger as _logger:
            monitoring_service = MonitoringService(site_checker, app_logger)

            return [result async for result in monitoring_service.monitor_sites(config.sites)]

    # Patch and run
    with patch.object(app, "run", side_effect=mock_run):
        results: list[SiteCheckResult] = await app.run(temp_config_file)

    # Verify results
    assert len(results) == 1

    # Check timeout site
    timeout_result = next(r for r in results)
    assert timeout_result.status == CheckStatus.TIMEOUT_ERROR
    assert timeout_result.response_time_ms is not None
    assert timeout_result.response_time_ms > 0
    assert timeout_result.error_message is not None


@pytest.mark.asyncio
async def test_monitoring_application_should_catch_content_validation(
    temp_config_file: Path, temp_log_file: Generator[Path]
) -> None:
    """Test the complete site monitoring workflow with real HTTP requests.
    This test will:
    GIVEN: Test data is set up and MonitoringApplication is initialized with a configuration file.
    WHEN: The monitoring application is run
    THEN: It should successfully check the site, log results, and handle content validation.

    """

    config_data = {
        "check_interval": 1,
        "log_file": str(temp_log_file),
        "retry": {"enabled": False},
        "sites": [
            {
                "url": "https://httpbin.org/html",
                "content_requirements": ["Nonexistent Content"],
                "timeout": 5,
                "require_all_content": True,
            },
        ],
    }

    # Write configuration to file
    with temp_config_file.open("w") as f:
        yaml.dump(config_data, f)

    # Create application components
    config_loader = FileConfigLoader()
    config = config_loader.load_config(temp_config_file)
    app_logger = AsyncMock(spec=FileLogger)
    app = MonitoringApplication(config, HttpSiteChecker(), app_logger)

    # Mock the run method to execute monitoring once
    async def mock_run(
        _config_path: Any,
        _check_interval: Any = None,
        _log_file: str | Path | None = None,
        _verbose: bool = False,
    ) -> list[SiteCheckResult]:
        async with HttpSiteChecker().with_session() as site_checker, app_logger as _logger:
            monitoring_service = MonitoringService(site_checker, app_logger)

            return [result async for result in monitoring_service.monitor_sites(config.sites)]

    # Patch and run
    with patch.object(app, "run", side_effect=mock_run):
        results: list[SiteCheckResult] = await app.run(temp_config_file)

    # Verify results
    assert len(results) == 1

    # Check content validation failure
    failure_result = next(r for r in results)
    assert failure_result.status == CheckStatus.CONTENT_ERROR
    assert failure_result.response_time_ms is not None
    assert failure_result.response_time_ms > 0
    assert failure_result.error_message is not None


@pytest.mark.asyncio
async def test_monitoring_application_should_catch_server_error(
    temp_config_file: Path, temp_log_file: Generator[Path]
) -> None:
    """Test the complete site monitoring workflow with real HTTP requests.
    This test will:
    GIVEN: Test data is set up and MonitoringApplication is initialized with a configuration file.
    WHEN: The monitoring application is run
    THEN: It should successfully check the site, log results, and handle server errors.

    """

    config_data = {
        "check_interval": 1,
        "log_file": str(temp_log_file),
        "retry": {"enabled": False},
        "sites": [
            {
                "url": "https://httpbin.org/status/500",
                "content_requirements": ["Herman Melville"],
                "timeout": 5,
                "require_all_content": True,
            },
        ],
    }

    # Write configuration to file
    with temp_config_file.open("w") as f:
        yaml.dump(config_data, f)

    # Create application components
    config_loader = FileConfigLoader()
    config = config_loader.load_config(temp_config_file)
    app_logger = AsyncMock(spec=FileLogger)
    app = MonitoringApplication(config, HttpSiteChecker(), app_logger)

    # Mock the run method to execute monitoring once
    async def mock_run(
        _config_path: Any,
        _check_interval: Any = None,
        _log_file: str | Path | None = None,
        _verbose: bool = False,
    ) -> list[SiteCheckResult]:
        async with HttpSiteChecker().with_session() as site_checker, app_logger as _logger:
            monitoring_service = MonitoringService(site_checker, app_logger)

            return [result async for result in monitoring_service.monitor_sites(config.sites)]

    # Patch and run
    with patch.object(app, "run", side_effect=mock_run):
        results: list[SiteCheckResult] = await app.run(temp_config_file)

    # Verify results
    assert len(results) == 1

    # Check server error site
    server_error_result = next(r for r in results)
    assert server_error_result.status == CheckStatus.SERVER_ERROR
    assert server_error_result.response_time_ms is not None
    assert server_error_result.response_time_ms == 0
    assert server_error_result.error_message is not None


@pytest.mark.asyncio
async def test_monitoring_application_should_handle_empty_config(
    temp_config_file: Path,
    temp_log_file: Generator[Path],  # noqa: ARG001
) -> None:
    """Test the monitoring application with an empty configuration.
    This test will:
    GIVEN: A configuration file with no sites.
    WHEN: The monitoring application is run
    THEN: It should handle the empty configuration gracefully without crashing.

    """

    # Write configuration to file
    with temp_config_file.open("w") as f:
        yaml.dump("", f)

    # Create application components
    config_loader = FileConfigLoader()
    with pytest.raises(ValueError):
        config_loader.load_config(temp_config_file)


@pytest.mark.asyncio
async def test_monitoring_application_should_handle_invalid_url(
    temp_config_file: Path, temp_log_file: Generator[Path]
) -> None:
    """Test the monitoring application with an invalid URL.
    This test will:
    GIVEN: A configuration file with an invalid URL.
    WHEN: The monitoring application is run
    THEN: It should handle the invalid URL gracefully without crashing.

    """

    config_data = {
        "check_interval": 1,
        "log_file": str(temp_log_file),
        "retry": {"enabled": False},
        "sites": [
            {
                "url": "invalid-url",
                "content_requirements": ["Herman Melville"],
                "timeout": 5,
                "require_all_content": True,
            },
        ],
    }

    # Write configuration to file
    with temp_config_file.open("w") as f:
        yaml.dump(config_data, f)

    # Create application components
    config_loader = FileConfigLoader()

    # Run the application and expect it to handle the invalid URL without crashing
    with pytest.raises(ValidationError):
        config_loader.load_config(temp_config_file)


@pytest.mark.asyncio
async def test_monitoring_application_should_handle_missing_content_requirements(
    temp_config_file: Path, temp_log_file: Generator[Path]
) -> None:
    """Test the monitoring application with missing content requirements.
    This test will:
    GIVEN: A configuration file with a site that has no content requirements.
    WHEN: The monitoring application is run
    THEN: It should raise a ValueError indicating that at least one content requirement must be specified.

    """

    config_data = {
        "check_interval": 1,
        "log_file": str(temp_log_file),
        "retry": {"enabled": False},
        "sites": [
            {
                "url": "https://httpbin.org/html",
                "timeout": 5,
                "require_all_content": True,
            },
        ],
    }

    # Write configuration to file
    with temp_config_file.open("w") as f:
        yaml.dump(config_data, f)

    # Create application components
    config_loader = FileConfigLoader()

    # Run the application and expect it to raise a ValueError
    with pytest.raises(ValueError, match="At least one content requirement must be specified"):
        config_loader.load_config(temp_config_file)
