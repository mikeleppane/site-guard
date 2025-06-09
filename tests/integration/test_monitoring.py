from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from site_guard.application.monitoring_app import MonitoringApplication
from site_guard.domain.models.result import SiteCheckResult
from site_guard.domain.models.status import CheckStatus
from site_guard.domain.services.monitoring import MonitoringService
from site_guard.infrastructure.http.checker import HttpSiteChecker
from site_guard.infrastructure.logging.logger import FileLogger
from site_guard.infrastructure.persistence.config import FileConfigLoader


@pytest.mark.asyncio
async def test_monitoring_application_should_catch_successful_request_(
    temp_config_file: Generator[Path], temp_log_file: Generator[Path]
):
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
    with open(temp_config_file, "w") as f:
        yaml.dump(config_data, f)

    # Create application components
    config_loader = FileConfigLoader()
    config = config_loader.load_config(temp_config_file)
    app_logger = AsyncMock(spec=FileLogger)
    app = MonitoringApplication(config, HttpSiteChecker(), app_logger)

    # Mock the run method to execute monitoring once
    async def mock_run(config_path, check_interval=None, log_file=None, verbose=False):
        async with HttpSiteChecker().with_session() as site_checker, app_logger as logger:
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
