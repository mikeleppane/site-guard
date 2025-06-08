from datetime import datetime

import pytest
from pydantic import HttpUrl

from site_guard.domain.models.result import SiteCheckResult
from site_guard.domain.models.status import CheckStatus


def test_create_successful_result() -> None:
    """Test creating a successful check result."""
    timestamp = datetime.now()
    result = SiteCheckResult(
        url=HttpUrl("https://example.com"),
        status=CheckStatus.SUCCESS,
        response_time_ms=250,
        timestamp=timestamp,
    )

    assert str(result.url) == "https://example.com"
    assert result.status == CheckStatus.SUCCESS
    assert result.response_time_ms == 250
    assert result.timestamp == timestamp
    assert result.error_message is None
    assert result.failed_content_requirements is None


def test_create_error_result() -> None:
    """Test creating an error check result."""
    timestamp = datetime.now()
    result = SiteCheckResult(
        url=HttpUrl("https://example.com"),
        status=CheckStatus.CONNECTION_ERROR,
        response_time_ms=5000,
        timestamp=timestamp,
        error_message="Connection timeout",
        failed_content_requirements=["Python", "programming"],
    )

    assert str(result.url) == "https://example.com"
    assert result.status == CheckStatus.CONNECTION_ERROR
    assert result.response_time_ms == 5000
    assert result.error_message == "Connection timeout"
    assert result.failed_content_requirements == ["Python", "programming"]


def test_property_methods() -> None:
    """Test property methods on SiteCheckResult."""
    timestamp = datetime.now()

    # Success result
    success_result = SiteCheckResult(
        url=HttpUrl("https://example.com"),
        status=CheckStatus.SUCCESS,
        response_time_ms=200,
        timestamp=timestamp,
    )

    assert success_result.is_success is True
    assert success_result.is_connection_error is False
    assert success_result.is_content_error is False

    # Connection error result
    conn_error_result = SiteCheckResult(
        url=HttpUrl("https://example.com"),
        status=CheckStatus.CONNECTION_ERROR,
        response_time_ms=None,
        timestamp=timestamp,
    )

    assert conn_error_result.is_success is False
    assert conn_error_result.is_connection_error is True
    assert conn_error_result.is_content_error is False

    # Content error result
    content_error_result = SiteCheckResult(
        url=HttpUrl("https://example.com"),
        status=CheckStatus.CONTENT_ERROR,
        response_time_ms=150,
        timestamp=timestamp,
    )

    assert content_error_result.is_success is False
    assert content_error_result.is_connection_error is False
    assert content_error_result.is_content_error is True


def test_result_immutability() -> None:
    """Test that SiteCheckResult is immutable (frozen dataclass)."""
    timestamp = datetime.now()
    result = SiteCheckResult(
        url=HttpUrl("https://example.com"),
        status=CheckStatus.SUCCESS,
        response_time_ms=200,
        timestamp=timestamp,
    )

    # Should not be able to modify fields
    with pytest.raises(AttributeError):
        result.url = HttpUrl("https://different.com")  # type: ignore[misc]

    with pytest.raises(AttributeError):
        result.status = CheckStatus.CONNECTION_ERROR  # type: ignore[misc]
