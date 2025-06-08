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
