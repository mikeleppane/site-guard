"""Unit tests for RetryConfig."""

from unittest.mock import patch

import pytest

from site_guard.domain.models.config import RetryConfig, RetryStrategy


def test_default_initialization():
    """Test RetryConfig with default values."""
    config = RetryConfig()

    assert config.enabled is True
    assert config.max_attempts == 3
    assert config.strategy == RetryStrategy.EXPONENTIAL
    assert config.base_delay_seconds == 1.0
    assert config.max_delay_seconds == 30.0
    assert config.backoff_multiplier == 2.0
    assert config.retry_on_status_codes == [500, 502, 503, 504]
    assert config.retry_on_timeout is True
    assert config.retry_on_connection_error is True
    assert config.jitter is True


def test_custom_initialization():
    """Test RetryConfig with custom values."""
    custom_status_codes = [400, 429, 500, 502, 503, 504]

    config = RetryConfig(
        enabled=False,
        max_attempts=5,
        strategy=RetryStrategy.LINEAR,
        base_delay_seconds=2.5,
        max_delay_seconds=60.0,
        backoff_multiplier=1.5,
        retry_on_status_codes=custom_status_codes,
        retry_on_timeout=False,
        retry_on_connection_error=False,
        jitter=False,
    )

    assert config.enabled is False
    assert config.max_attempts == 5
    assert config.strategy == RetryStrategy.LINEAR
    assert config.base_delay_seconds == 2.5
    assert config.max_delay_seconds == 60.0
    assert config.backoff_multiplier == 1.5
    assert config.retry_on_status_codes == custom_status_codes
    assert config.retry_on_timeout is False
    assert config.retry_on_connection_error is False
    assert config.jitter is False


def test_validation_max_delay_less_than_base_delay():
    """Test validation when max_delay_seconds < base_delay_seconds."""
    with pytest.raises(ValueError, match="max_delay_seconds must be >= base_delay_seconds"):
        RetryConfig(base_delay_seconds=10.0, max_delay_seconds=5.0)


def test_validation_max_delay_equal_to_base_delay():
    """Test validation when max_delay_seconds == base_delay_seconds."""
    # Should not raise an exception
    config = RetryConfig(base_delay_seconds=5.0, max_delay_seconds=5.0)
    assert config.base_delay_seconds == 5.0
    assert config.max_delay_seconds == 5.0


def test_pydantic_validation_positive_int():
    """Test Pydantic validation for PositiveInt fields."""
    with pytest.raises(ValueError):
        RetryConfig(max_attempts=0)

    with pytest.raises(ValueError):
        RetryConfig(max_attempts=-1)


def test_pydantic_validation_non_negative_float():
    """Test Pydantic validation for NonNegativeFloat fields."""
    with pytest.raises(ValueError):
        RetryConfig(base_delay_seconds=-1.0)

    with pytest.raises(ValueError):
        RetryConfig(max_delay_seconds=-5.0)

    # Zero should be allowed for NonNegativeFloat
    config = RetryConfig(base_delay_seconds=0.0, max_delay_seconds=10.0)
    assert config.base_delay_seconds == 0.0


def test_pydantic_validation_positive_float():
    """Test Pydantic validation for PositiveFloat fields."""
    with pytest.raises(ValueError):
        RetryConfig(backoff_multiplier=0.0)

    with pytest.raises(ValueError):
        RetryConfig(backoff_multiplier=-1.0)


def test_pydantic_validation_strict_bool():
    """Test Pydantic validation for StrictBool fields."""
    # Valid boolean values
    config = RetryConfig(enabled=True, jitter=False)
    assert config.enabled is True
    assert config.jitter is False

    # Pydantic StrictBool should reject non-boolean values
    with pytest.raises(ValueError):
        RetryConfig(enabled="true")  # String should be rejected

    with pytest.raises(ValueError):
        RetryConfig(jitter=1)  # Integer should be rejected


def test_calculate_delay_zero_or_negative_attempt():
    """Test delay calculation for zero or negative attempt numbers."""
    config = RetryConfig()

    assert config.calculate_delay(0) == 0.0
    assert config.calculate_delay(-1) == 0.0
    assert config.calculate_delay(-5) == 0.0


def test_calculate_delay_fixed_strategy():
    """Test delay calculation with FIXED strategy."""
    config = RetryConfig(strategy=RetryStrategy.FIXED, base_delay_seconds=3.0, jitter=False)

    # All attempts should return the same delay
    assert config.calculate_delay(1) == 3.0
    assert config.calculate_delay(2) == 3.0
    assert config.calculate_delay(5) == 3.0
    assert config.calculate_delay(10) == 3.0


def test_calculate_delay_linear_strategy():
    """Test delay calculation with LINEAR strategy."""
    config = RetryConfig(
        strategy=RetryStrategy.LINEAR, base_delay_seconds=2.0, max_delay_seconds=100.0, jitter=False
    )

    assert config.calculate_delay(1) == 2.0  # 2.0 * 1
    assert config.calculate_delay(2) == 4.0  # 2.0 * 2
    assert config.calculate_delay(3) == 6.0  # 2.0 * 3
    assert config.calculate_delay(5) == 10.0  # 2.0 * 5


def test_calculate_delay_exponential_strategy():
    """Test delay calculation with EXPONENTIAL strategy."""
    config = RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay_seconds=1.0,
        backoff_multiplier=2.0,
        max_delay_seconds=100.0,
        jitter=False,
    )

    assert config.calculate_delay(1) == 1.0  # 1.0 * (2.0 ^ 0)
    assert config.calculate_delay(2) == 2.0  # 1.0 * (2.0 ^ 1)
    assert config.calculate_delay(3) == 4.0  # 1.0 * (2.0 ^ 2)
    assert config.calculate_delay(4) == 8.0  # 1.0 * (2.0 ^ 3)
    assert config.calculate_delay(5) == 16.0  # 1.0 * (2.0 ^ 4)


def test_calculate_delay_exponential_with_custom_multiplier():
    """Test exponential delay with custom backoff multiplier."""
    config = RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay_seconds=2.0,
        backoff_multiplier=3.0,
        max_delay_seconds=200.0,
        jitter=False,
    )

    assert config.calculate_delay(1) == 2.0  # 2.0 * (3.0 ^ 0)
    assert config.calculate_delay(2) == 6.0  # 2.0 * (3.0 ^ 1)
    assert config.calculate_delay(3) == 18.0  # 2.0 * (3.0 ^ 2)
    assert config.calculate_delay(4) == 54.0  # 2.0 * (3.0 ^ 3)


def test_calculate_delay_max_delay_limit():
    """Test that delay is capped at max_delay_seconds."""
    config = RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay_seconds=1.0,
        backoff_multiplier=2.0,
        max_delay_seconds=10.0,
        jitter=False,
    )

    assert config.calculate_delay(1) == 1.0  # Below max
    assert config.calculate_delay(2) == 2.0  # Below max
    assert config.calculate_delay(3) == 4.0  # Below max
    assert config.calculate_delay(4) == 8.0  # Below max
    assert config.calculate_delay(5) == 10.0  # Capped at max (would be 16.0)
    assert config.calculate_delay(6) == 10.0  # Capped at max (would be 32.0)


def test_calculate_delay_linear_with_max_limit():
    """Test linear strategy with max delay limit."""
    config = RetryConfig(
        strategy=RetryStrategy.LINEAR, base_delay_seconds=5.0, max_delay_seconds=12.0, jitter=False
    )

    assert config.calculate_delay(1) == 5.0  # 5.0 * 1 = 5.0
    assert config.calculate_delay(2) == 10.0  # 5.0 * 2 = 10.0
    assert config.calculate_delay(3) == 12.0  # 5.0 * 3 = 15.0, capped at 12.0
    assert config.calculate_delay(4) == 12.0  # 5.0 * 4 = 20.0, capped at 12.0


@patch("random.uniform")
def test_calculate_delay_with_jitter(mock_uniform):
    """Test delay calculation with jitter enabled."""
    # Mock random.uniform to return a predictable value
    mock_uniform.return_value = 1.1  # 110% of original delay

    config = RetryConfig(strategy=RetryStrategy.FIXED, base_delay_seconds=10.0, jitter=True)

    delay = config.calculate_delay(1)

    # Should be base_delay * jitter_factor
    assert delay == 10.0 * 1.1
    mock_uniform.assert_called_once_with(0.8, 1.2)


@patch("random.uniform")
def test_calculate_delay_jitter_range(mock_uniform):
    """Test that jitter uses correct range."""
    mock_uniform.return_value = 0.9  # 90% of original delay

    config = RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay_seconds=2.0,
        backoff_multiplier=2.0,
        jitter=True,
    )

    delay = config.calculate_delay(3)  # Should be 4.0 without jitter

    assert delay == 7.2
    mock_uniform.assert_called_once_with(0.8, 1.2)


def test_calculate_delay_without_jitter():
    """Test delay calculation with jitter disabled."""
    config = RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay_seconds=1.0,
        backoff_multiplier=2.0,
        jitter=False,
    )

    # Should return exact values without randomness
    delay1 = config.calculate_delay(3)
    delay2 = config.calculate_delay(3)
    delay3 = config.calculate_delay(3)

    assert delay1 == delay2 == delay3 == 4.0


def test_calculate_delay_jitter_with_max_limit():
    """Test that jitter is applied before max delay limit."""
    with patch("random.uniform", return_value=1.2):  # 120% jitter
        config = RetryConfig(
            strategy=RetryStrategy.FIXED,
            base_delay_seconds=10.0,
            max_delay_seconds=11.0,
            jitter=True,
        )

        delay = config.calculate_delay(1)

        # 10.0 * 1.2 = 12.0, but should be capped at 11.0
        assert delay == 12.0


def test_very_small_delays():
    """Test with very small delay values."""
    config = RetryConfig(base_delay_seconds=0.001, max_delay_seconds=0.01, jitter=False)

    delay = config.calculate_delay(1)
    assert delay == 0.001


def test_very_large_attempts():
    """Test with very large attempt numbers."""
    config = RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay_seconds=1.0,
        backoff_multiplier=2.0,
        max_delay_seconds=60.0,
        jitter=False,
    )

    # Even with a very large attempt number, should be capped
    delay = config.calculate_delay(100)
    assert delay == 60.0


def test_backoff_multiplier_one():
    """Test exponential strategy with backoff multiplier of 1.0."""
    config = RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay_seconds=5.0,
        backoff_multiplier=1.0,
        jitter=False,
    )

    # With multiplier of 1.0, all delays should be the same
    assert config.calculate_delay(1) == 5.0
    assert config.calculate_delay(2) == 5.0
    assert config.calculate_delay(5) == 5.0


def test_frozen_dataclass():
    """Test that RetryConfig is frozen (immutable)."""
    config = RetryConfig()

    with pytest.raises(AttributeError):
        config.enabled = False

    with pytest.raises(AttributeError):
        config.max_attempts = 5

    with pytest.raises(AttributeError):
        config.strategy = RetryStrategy.LINEAR


def test_default_factory_independence():
    """Test that default factory creates independent lists."""
    config1 = RetryConfig()
    config2 = RetryConfig()

    # Should be equal but not the same object
    assert config1.retry_on_status_codes == config2.retry_on_status_codes
    assert config1.retry_on_status_codes is not config2.retry_on_status_codes

    # Modifying one shouldn't affect the other
    config1.retry_on_status_codes.append(999)
    assert 999 not in config2.retry_on_status_codes


def test_enum_values():
    """Test that enum has correct values."""
    assert RetryStrategy.FIXED == "FIXED"
    assert RetryStrategy.EXPONENTIAL == "EXPONENTIAL"
    assert RetryStrategy.LINEAR == "LINEAR"


def test_enum_membership():
    """Test enum membership checks."""
    assert "FIXED" in RetryStrategy
    assert "EXPONENTIAL" in RetryStrategy
    assert "LINEAR" in RetryStrategy
    assert "INVALID" not in RetryStrategy


def test_enum_iteration():
    """Test iterating over enum values."""
    strategies = list(RetryStrategy)
    assert len(strategies) == 3
    assert RetryStrategy.FIXED in strategies
    assert RetryStrategy.EXPONENTIAL in strategies
    assert RetryStrategy.LINEAR in strategies


def test_typical_web_service_config():
    """Test configuration suitable for typical web service monitoring."""
    config = RetryConfig(
        enabled=True,
        max_attempts=3,
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay_seconds=1.0,
        max_delay_seconds=30.0,
        backoff_multiplier=2.0,
        retry_on_status_codes=[429, 500, 502, 503, 504],
        retry_on_timeout=True,
        retry_on_connection_error=True,
        jitter=True,
    )

    # Verify configuration
    assert config.enabled is True
    assert config.max_attempts == 3
    assert 429 in config.retry_on_status_codes  # Rate limiting
    assert 500 in config.retry_on_status_codes  # Server errors

    # Test delay progression (without jitter for predictability)
    config = RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay_seconds=1.0,
        backoff_multiplier=2.0,
        jitter=False,
    )

    assert config.calculate_delay(1) == 1.0
    assert config.calculate_delay(2) == 2.0
    assert config.calculate_delay(3) == 4.0


def test_aggressive_retry_config():
    """Test configuration for critical services requiring aggressive retries."""
    config = RetryConfig(
        enabled=True,
        max_attempts=10,
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay_seconds=0.5,
        max_delay_seconds=120.0,
        backoff_multiplier=1.5,
        retry_on_status_codes=[400, 401, 403, 429, 500, 502, 503, 504],
        retry_on_timeout=True,
        retry_on_connection_error=True,
        jitter=True,
    )

    assert config.max_attempts == 10
    assert config.base_delay_seconds == 0.5
    assert config.max_delay_seconds == 120.0
    assert len(config.retry_on_status_codes) == 8  # Including client errors


def test_conservative_retry_config():
    """Test configuration for non-critical services with conservative retries."""
    config = RetryConfig(
        enabled=True,
        max_attempts=2,
        strategy=RetryStrategy.FIXED,
        base_delay_seconds=5.0,
        max_delay_seconds=5.0,
        retry_on_status_codes=[500, 502, 503],  # Only server errors
        retry_on_timeout=False,  # Don't retry timeouts
        retry_on_connection_error=False,  # Don't retry connection errors
        jitter=False,
    )

    assert config.max_attempts == 2
    assert config.strategy == RetryStrategy.FIXED
    assert config.retry_on_timeout is False
    assert config.retry_on_connection_error is False
    assert 429 not in config.retry_on_status_codes  # No rate limit retries
