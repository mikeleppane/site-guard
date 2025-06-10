import pytest
from pydantic import HttpUrl, ValidationError

from site_guard.domain.models.config import MonitoringConfig, SiteConfig


def test_create_monitoring_config() -> None:
    """Test creating a monitoring configuration."""
    sites = [
        SiteConfig(url="https://example.com", content_requirements=["Welcome"]),
        SiteConfig(url="https://python.org", content_requirements=["Python"]),
    ]

    config = MonitoringConfig(check_interval=60, sites=sites, log_file="test.log")

    assert config.check_interval == 60
    assert len(config.sites) == 2
    assert config.log_file == "test.log"


def test_default_values() -> None:
    """Test default values in monitoring configuration."""
    sites = [SiteConfig(url=HttpUrl("https://example.com"), content_requirements=["test"])]
    config = MonitoringConfig(sites=sites)

    assert config.check_interval == 60  # default
    assert config.log_file == "site_guard.log"  # default


def test_invalid_check_interval() -> None:
    """Test that invalid check intervals are rejected."""
    sites = [SiteConfig(url="https://example.com", content_requirements=["test"])]

    MonitoringConfig(sites=sites, check_interval=0)

    with pytest.raises(ValidationError) as exc_info:
        MonitoringConfig(sites=sites, check_interval=-10)

    assert "Input should be greater than or equal to 0" in str(exc_info.value)


def test_empty_sites_list() -> None:
    """Test handling of empty sites list."""
    config = MonitoringConfig(sites=[])
    assert config.sites == []
    assert config.sites == []


def test_with_overridden_interval() -> None:
    """Test creating a config with overridden check interval."""
    sites = [SiteConfig(url="https://example.com", content_requirements=["test"])]
    config = MonitoringConfig(sites=sites, check_interval=120)

    new_config = config.with_overridden_interval(30)
    assert new_config.check_interval == 30
    assert config.check_interval == 120
    assert config is not new_config


def test_with_overridden_interval_invalid() -> None:
    """Test that invalid overridden intervals raise an error."""
    sites = [SiteConfig(url="https://example.com", content_requirements=["test"])]
    config = MonitoringConfig(sites=sites, check_interval=60)

    with pytest.raises(ValueError):
        config.with_overridden_interval(-150.5)  # Negative interval
    with pytest.raises(ValueError):
        config.with_overridden_interval(-1)  # Zero interval
    with pytest.raises(ValueError):
        config.with_overridden_interval("invalid")
