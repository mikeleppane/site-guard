import pytest
from pydantic import ValidationError

from site_guard.domain.models.config import SiteConfig
from site_guard.domain.models.content import ContentRequirement


def test_create_simple_site_config() -> None:
    """Test creating a simple site configuration."""
    config = SiteConfig(url="https://example.com", content_requirements=["Welcome"])

    assert str(config.url) == "https://example.com/"
    assert len(config.content_requirements) == 1
    assert isinstance(config.content_requirements[0], ContentRequirement)
    assert config.content_requirements[0].pattern == "Welcome"
    assert config.timeout == 30  # default
    assert config.require_all_content is True  # default


def test_create_complex_site_config() -> None:
    """Test creating a complex site configuration."""
    requirements = [
        ContentRequirement(pattern="Python", case_sensitive=True),
        ContentRequirement(pattern="*programming*", use_wildcards=True),
    ]

    config = SiteConfig(
        url="https://python.org",
        content_requirements=requirements,
        timeout=60,
        require_all_content=False,
    )

    assert str(config.url) == "https://python.org/"
    assert len(config.content_requirements) == 2
    assert config.timeout == 60
    assert config.require_all_content is False


def test_mixed_content_requirements() -> None:
    """Test mixing string and ContentRequirement objects."""
    config = SiteConfig(
        url="https://example.com",
        content_requirements=[
            "Simple string",
            ContentRequirement(pattern="*wildcard*", use_wildcards=True),
        ],
    )

    assert len(config.content_requirements) == 2
    assert isinstance(config.content_requirements[0], ContentRequirement)
    assert isinstance(config.content_requirements[1], ContentRequirement)
    assert config.content_requirements[0].pattern == "Simple string"
    assert config.content_requirements[0].use_wildcards is False
    assert config.content_requirements[1].pattern == "*wildcard*"
    assert config.content_requirements[1].use_wildcards is True


def test_empty_content_requirements() -> None:
    """Test that empty content requirements are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        SiteConfig(url="https://example.com", content_requirements=[])

    assert "At least one content requirement must be specified" in str(exc_info.value)


def test_invalid_url() -> None:
    """Test that invalid URLs are rejected."""
    with pytest.raises(ValidationError):
        SiteConfig(url="not-a-valid-url", content_requirements=["test"])

    with pytest.raises(ValidationError):
        SiteConfig(url="", content_requirements=["test"])


def test_check_content_requirements_all_match() -> None:
    """Test content checking when all requirements must match."""
    config = SiteConfig(
        url="https://example.com",
        content_requirements=[
            "Python",
            ContentRequirement(pattern="*programming*", use_wildcards=True),
        ],
        require_all_content=True,
    )

    # All requirements match
    res = config.check_content_requirements("Learn Python programming today")
    assert res.success is True
    assert res.failed_patterns == []

    # One requirement fails
    res = config.check_content_requirements("Learn Python today")
    assert res.success is False
    assert res.failed_patterns == ["*programming*"]

    # All requirements fail
    res = config.check_content_requirements("Learn Java development")
    assert res.success is False
    assert set(res.failed_patterns) == {"Python", "*programming*"}


def test_check_content_requirements_any_match() -> None:
    """Test content checking when any requirement can match."""
    config = SiteConfig(
        url="https://example.com",
        content_requirements=["Python", "Java", "JavaScript"],
        require_all_content=False,
    )

    # One requirement matches
    res = config.check_content_requirements("Learn Python today")
    assert res.success is True
    assert set(res.failed_patterns) == {"Java", "JavaScript"}

    # Multiple requirements match
    res = config.check_content_requirements("Python and Java programming")
    assert res.success is True
    assert res.failed_patterns == ["JavaScript"]

    # No requirements match
    res = config.check_content_requirements("Learn C++ programming")
    assert res.success is False
    assert set(res.failed_patterns) == {"Python", "Java", "JavaScript"}


# improve site_config unit tests
def test_retry_config_defaults() -> None:
    """Test default retry configuration."""
    config = SiteConfig(url="https://example.com", content_requirements=["test"])

    assert config.retry_config.max_attempts == 3
    assert config.retry_config.base_delay_seconds == 1.0
    assert config.retry_config.backoff_multiplier == 2.0


def test_retry_config_custom_values() -> None:
    """Test custom retry configuration values."""
    config = SiteConfig(
        url="https://example.com",
        content_requirements=["test"],
        retry_config={
            "max_attempts": 5,
            "base_delay_seconds": 10.0,
            "backoff_multiplier": 1.5,
        },
    )

    assert config.retry_config.max_attempts == 5
    assert config.retry_config.base_delay_seconds == 10.0
    assert config.retry_config.backoff_multiplier == 1.5


def test_retry_config_invalid_values() -> None:
    """Test that invalid retry configuration values raise errors."""
    with pytest.raises(ValidationError):
        SiteConfig(
            url="https://example.com",
            content_requirements=["test"],
            retry_config={
                "max_attempts": -1,  # Invalid negative value
                "base_delay_seconds": 5.0,
                "backoff_multiplier": 2.0,
            },
        )

    with pytest.raises(ValidationError):
        SiteConfig(
            url="https://example.com",
            content_requirements=["test"],
            retry_config={
                "max_attempts": 3,
                "base_delay_seconds": -5.0,  # Invalid negative value
                "backoff_multiplier": 2.0,
            },
        )


def test_retry_config_max_retries_zero() -> None:
    """Test that max_retries can be set to zero."""
    with pytest.raises(ValidationError):
        SiteConfig(
            url="https://example.com",
            content_requirements=["test"],
            retry_config={
                "max_attempts": 0,
                "base_delay_seconds": 5.0,
                "backoff_multiplier": 2.0,
            },
        )


def test_retry_config_max_retries_one() -> None:
    """Test that max_retries can be set to one."""
    config = SiteConfig(
        url="https://example.com",
        content_requirements=["test"],
        retry_config={
            "max_attempts": 1,
            "base_delay_seconds": 5.0,
            "backoff_multiplier": 2.0,
        },
    )

    assert config.retry_config.max_attempts == 1
    assert config.retry_config.base_delay_seconds == 5.0
    assert config.retry_config.backoff_multiplier == 2.0


def test_retry_config_max_retries_large() -> None:
    """Test that max_retries can be set to a large value."""
    config = SiteConfig(
        url="https://example.com",
        content_requirements=["test"],
        retry_config={
            "max_attempts": 1000,
            "base_delay_seconds": 5.0,
            "backoff_multiplier": 2.0,
        },
    )

    assert config.retry_config.max_attempts == 1000
    assert config.retry_config.base_delay_seconds == 5.0
    assert config.retry_config.backoff_multiplier == 2.0


def test_retry_config_invalid_strategy() -> None:
    """Test that invalid retry strategies raise errors."""
    with pytest.raises(ValidationError):
        SiteConfig(
            url="https://example.com",
            content_requirements=["test"],
            retry_config={
                "max_attempts": 3,
                "base_delay_seconds": 5.0,
                "backoff_multiplier": 2.0,
                "strategy": "INVALID",  # Invalid strategy
            },
        )


def test_retry_config_exponential_backoff() -> None:
    """Test exponential backoff calculation."""
    config = SiteConfig(
        url="https://example.com",
        content_requirements=["test"],
        retry_config={
            "max_attempts": 3,
            "base_delay_seconds": 1.0,
            "backoff_multiplier": 2.0,
            "strategy": "EXPONENTIAL",
        },
    )

    assert config.retry_config.calculate_delay(1) < 2
    assert config.retry_config.calculate_delay(2) < 3
    assert config.retry_config.calculate_delay(3) < 5
    assert config.retry_config.calculate_delay(4) < 10


def test_retry_config_linear_backoff() -> None:
    """Test linear backoff calculation."""
    config = SiteConfig(
        url="https://example.com",
        content_requirements=["test"],
        retry_config={
            "max_attempts": 3,
            "base_delay_seconds": 1.0,
            "backoff_multiplier": 1.0,  # Not used in linear
            "strategy": "LINEAR",
        },
    )

    assert config.retry_config.calculate_delay(1) < 2
    assert config.retry_config.calculate_delay(2) < 3
    assert config.retry_config.calculate_delay(3) < 5
    assert config.retry_config.calculate_delay(4) < 6


def test_retry_config_fixed_backoff() -> None:
    """Test fixed backoff calculation."""
    config = SiteConfig(
        url="https://example.com",
        content_requirements=["test"],
        retry_config={
            "max_attempts": 3,
            "base_delay_seconds": 5.0,
            "backoff_multiplier": 1.0,  # Not used in fixed
            "strategy": "FIXED",
        },
    )

    assert config.retry_config.calculate_delay(1) < 6
    assert config.retry_config.calculate_delay(2) < 6
    assert config.retry_config.calculate_delay(3) < 6
    assert config.retry_config.calculate_delay(4) < 6


def test_retry_config_jitter_enabled() -> None:
    """Test that jitter is applied when enabled."""
    config = SiteConfig(
        url="https://example.com",
        content_requirements=["test"],
        retry_config={
            "max_attempts": 3,
            "base_delay_seconds": 1.0,
            "backoff_multiplier": 2.0,
            "strategy": "EXPONENTIAL",
            "jitter": True,
        },
    )

    delay = config.retry_config.calculate_delay(2)
    assert delay > 1.0 and delay < 4.0  # Jitter should modify the delay


def test_retry_config_jitter_disabled() -> None:
    """Test that no jitter is applied when disabled."""
    config = SiteConfig(
        url="https://example.com",
        content_requirements=["test"],
        retry_config={
            "max_attempts": 3,
            "base_delay_seconds": 1.0,
            "backoff_multiplier": 2.0,
            "strategy": "EXPONENTIAL",
            "jitter": False,
        },
    )

    delay = config.retry_config.calculate_delay(2)
    assert delay == 2.0  # No jitter should result in exact delay


def test_retry_config_max_delay() -> None:
    """Test that max_delay_seconds limits the delay."""
    config = SiteConfig(
        url="https://example.com",
        content_requirements=["test"],
        retry_config={
            "max_attempts": 3,
            "base_delay_seconds": 1.0,
            "backoff_multiplier": 2.0,
            "strategy": "EXPONENTIAL",
            "max_delay_seconds": 3.0,
        },
    )

    assert 0.5 < config.retry_config.calculate_delay(1) < 2
    assert 1.5 < config.retry_config.calculate_delay(2) < 3
    assert 2.5 < config.retry_config.calculate_delay(3) < 4
    assert 2 < config.retry_config.calculate_delay(4) < 5  # Should not exceed max delay
