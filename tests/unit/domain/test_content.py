import pytest
from pydantic import ValidationError

from site_guard.domain.models.config import (
    ContentRequirement,
    SiteConfig,
)


def test_create_simple_requirement() -> None:
    """Test creating a simple content requirement."""
    req = ContentRequirement(pattern="Python")

    assert req.pattern == "Python"
    assert req.use_wildcards is False
    assert req.case_sensitive is True


def test_create_wildcard_requirement() -> None:
    """Test creating a wildcard content requirement."""
    req = ContentRequirement(
        pattern="*Python*programming*", use_wildcards=True, case_sensitive=False
    )

    assert req.pattern == "*Python*programming*"
    assert req.use_wildcards is True
    assert req.case_sensitive is False


def test_empty_pattern_validation() -> None:
    """Test that empty patterns are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        ContentRequirement(pattern="")

    assert "Content requirement pattern cannot be empty" in str(exc_info.value)

    with pytest.raises(ValidationError):
        ContentRequirement(pattern="   ")  # Only whitespace


def test_pattern_trimming() -> None:
    """Test that patterns are automatically trimmed."""
    req = ContentRequirement(pattern="  Python  ")
    assert req.pattern == "Python"


def test_exact_match_case_sensitive() -> None:
    """Test exact matching with case sensitivity."""
    req = ContentRequirement(pattern="Python", case_sensitive=True)

    assert req.matches("Welcome to Python programming") is True
    assert req.matches("Welcome to python programming") is False
    assert req.matches("Welcome to PYTHON programming") is False
    assert req.matches("Welcome to Java programming") is False


def test_exact_match_case_insensitive() -> None:
    """Test exact matching without case sensitivity."""
    req = ContentRequirement(pattern="Python", case_sensitive=False)

    assert req.matches("Welcome to Python programming") is True
    assert req.matches("Welcome to python programming") is True
    assert req.matches("Welcome to PYTHON programming") is True
    assert req.matches("Welcome to Java programming") is False


def test_wildcard_match_case_sensitive() -> None:
    """Test wildcard matching with case sensitivity."""
    req = ContentRequirement(
        pattern="*Python*programming*", use_wildcards=True, case_sensitive=True
    )

    assert req.matches("Learn Python programming today") is True
    assert req.matches("Learn python programming today") is False
    assert req.matches("Python is great for programming") is True
    assert req.matches("Java programming is different") is False


def test_wildcard_match_case_insensitive() -> None:
    """Test wildcard matching without case sensitivity."""
    req = ContentRequirement(
        pattern="*Python*Programming*", use_wildcards=True, case_sensitive=False
    )

    assert req.matches("Learn Python programming today") is True
    assert req.matches("Learn python programming today") is True
    assert req.matches("PYTHON PROGRAMMING IS GREAT") is True
    assert req.matches("Java development is different") is False


def test_wildcard_single_character() -> None:
    """Test single character wildcard matching."""
    req = ContentRequirement(pattern="Pytho?", use_wildcards=True)

    assert req.matches("Python") is True
    assert req.matches("Pythod") is True
    assert req.matches("Pytho") is False
    assert req.matches("Pythons") is False
    assert req.matches("Pytho") is False
    assert req.matches("Pythons") is False
    assert req.matches("Pythons") is False


def test_content_requirement_immutability() -> None:
    """Test that ContentRequirement is immutable."""
    req = ContentRequirement(pattern="Python")

    # Should not be able to modify fields
    with pytest.raises(ValidationError):
        req.pattern = "Java"

    with pytest.raises(ValidationError):
        req.use_wildcards = True  # type: ignore[misc]

    with pytest.raises(ValidationError):
        req.case_sensitive = False  # type: ignore[misc]


def test_very_long_pattern() -> None:
    """Test handling of very long patterns."""
    long_pattern = "a" * 1000
    req = ContentRequirement(pattern=long_pattern)

    assert len(req.pattern) == 1000
    assert req.matches("a" * 1000) is True
    assert req.matches("a" * 999) is False


def test_unicode_patterns() -> None:
    """Test handling of Unicode patterns."""
    req = ContentRequirement(pattern="こんにちは", case_sensitive=True)

    assert req.matches("こんにちは世界") is True
    assert req.matches("Hello World") is False


def test_special_regex_characters() -> None:
    """Test handling of special regex characters in patterns."""
    req = ContentRequirement(pattern="C++ (advanced)", case_sensitive=True)

    assert req.matches("Learn C++ (advanced) programming") is True
    assert req.matches("Learn C programming") is False


def test_wildcard_with_special_characters() -> None:
    """Test wildcards with special characters."""
    req = ContentRequirement(pattern="*C++*programming*", use_wildcards=True, case_sensitive=True)

    assert req.matches("Learn C++ for programming") is True
    assert req.matches("Learn C programming") is False


def test_empty_content_matching() -> None:
    """Test pattern matching against empty content."""
    req = ContentRequirement(pattern="Python")

    assert req.matches("") is False
    assert req.matches("   ") is False


def test_site_config_with_maximum_timeout() -> None:
    """Test site config with very large timeout values."""
    config = SiteConfig(
        url="https://example.com",
        content_requirements=["test"],
        timeout=3600,  # 1 hour
    )

    assert config.timeout == 3600
