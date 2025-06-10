import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from site_guard.domain.models.config import MonitoringConfig, RetryConfig, RetryStrategy
from site_guard.domain.models.content import ContentRequirement
from site_guard.infrastructure.persistence.config import (
    FileConfigLoader,
    InvalidFileFormatError,
    InvalidJsonConfigError,
    InvalidRetryStrategyError,
)


def test_file_config_loader_with_valid_yaml() -> None:
    # Create a temporary YAML file with valid content
    yaml_content = """
    # config.yaml - Advanced configuration with multiple content requirements
check_interval: 30
log_file: "site_guard.log"
sites:
  - url: "https://www.python.org/"
    content_requirements: ["Python"]
    timeout: 15
  - url: "https://www.rust-lang.org/"
    content_requirements:
      - pattern: "Rust"
        case_sensitive: true
      - pattern: "programming language"
        case_sensitive: false
    require_all_content: true
    timeout: 15
  - url: "https://go.dev/"
    content_requirements:
      - pattern: "Go"
        case_sensitive: true
      - pattern: "*Build simple*"
        use_wildcards: true
        case_sensitive: false
    require_all_content: true
    timeout: 15
  - url: "https://www.modular.com/mojo"
    content_requirements:
      - pattern: "Mojo"
      - pattern: "Modular"
      - pattern: "AI"
    require_all_content: false  # Only one needs to match
    timeout: 15
  - url: "https://httpbin.org/html"
    content_requirements:
      - pattern: "*Herman*Melville*"
        use_wildcards: true
        case_sensitive: false
    timeout: 15
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=True) as fp:
        fp.write(yaml_content)
        fp.flush()
        temp_file = Path(fp.name)

        loader = FileConfigLoader()
        config = loader.load_config(temp_file)

        assert isinstance(config, MonitoringConfig)
        assert config.check_interval == 30
        assert config.log_file == "site_guard.log"
        assert len(config.sites) == 5


def test_file_config_loader_with_valid_json() -> None:
    # Create a temporary JSON file with valid content
    json_content = """
    {
        "check_interval": 30,
        "log_file": "site_guard.log",
        "sites": [
            {
                "url": "https://www.python.org/",
                "content_requirements": ["Python"],
                "timeout": 15
            },
            {
                "url": "https://www.rust-lang.org/",
                "content_requirements": [
                    {"pattern": "Rust", "case_sensitive": true},
                    {"pattern": "programming language", "case_sensitive": false}
                ],
                "require_all_content": true,
                "timeout": 15
            }
        ]
    }
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=True) as fp:
        fp.write(json_content)
        fp.flush()
        temp_file = Path(fp.name)

        loader = FileConfigLoader()
        config = loader.load_config(temp_file)

        assert isinstance(config, MonitoringConfig)
        assert config.check_interval == 30
        assert config.log_file == "site_guard.log"
        assert len(config.sites) == 2


def test_file_config_loader_with_invalid_json() -> None:
    # Create a temporary JSON file with invalid content
    invalid_json_content = """
    {
        "check_interval": 30,
        "log_file": "site_guard.log",
        "sites": [
            {
                "url": "https://www.python.org/",
                "content_requirements": ["Python"],
                "timeout": 15
            },
            {
                "url": "https://www.rust-lang.org/",
                "content_requirements": [
                    {"pattern": "Rust", "case_sensitive": true},
                    {"pattern": "programming language", "case_sensitive": false
                ],
                "require_all_content": true,
                "timeout": 15
            }
        ]
    }
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=True) as fp:
        fp.write(invalid_json_content)
        fp.flush()
        temp_file = Path(fp.name)

        loader = FileConfigLoader()
        with pytest.raises(InvalidJsonConfigError):
            loader.load_config(temp_file)


def test_file_config_loader_invalid_model_data(file_config_loader: FileConfigLoader) -> None:
    # Create a temporary YAML file with invalid model data
    invalid_yaml_content = """
    check_interval: 30
    log_file: "site_guard.log"
    sites:
      - url: "https://www.python.org/"
        content_requirements: ["Python"]
        timeout: "invalid_timeout"  # Invalid type
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=True) as fp:
        fp.write(invalid_yaml_content)
        fp.flush()
        temp_file = Path(fp.name)

        with pytest.raises(ValidationError):
            file_config_loader.load_config(temp_file)


def test_load_config_file_not_found(file_config_loader: FileConfigLoader) -> None:
    """Test loading configuration from non-existent file."""
    non_existent_path = Path("/non/existent/config.yaml")

    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        file_config_loader.load_config(non_existent_path)


def test_load_config_unsupported_file_format(file_config_loader: FileConfigLoader) -> None:
    """Test loading configuration from unsupported file format."""
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as tmp_file:
        tmp_file.write("some content")
        tmp_path = Path(tmp_file.name)

    try:
        with pytest.raises(InvalidFileFormatError, match="Unsupported configuration file format"):
            file_config_loader.load_config(tmp_path)
    finally:
        tmp_path.unlink()


def test_load_valid_yaml_config(file_config_loader: FileConfigLoader) -> None:
    """Test loading valid YAML configuration."""
    config_data = {
        "check_interval": 30,
        "log_file": "test.log",
        "sites": [
            {
                "url": "https://example.com",
                "name": "Example Site",
                "timeout": 15,
                "content_requirements": ["Example Domain"],
            }
        ],
    }

    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as tmp_file:
        yaml.dump(config_data, tmp_file)
        tmp_path = Path(tmp_file.name)

    try:
        config = file_config_loader.load_config(tmp_path)

        assert isinstance(config, MonitoringConfig)
        assert config.check_interval == 30
        assert config.log_file == "test.log"
        assert len(config.sites) == 1
        assert str(config.sites[0].url) == "https://example.com/"
        assert config.sites[0].name == "Example Site"
        assert config.sites[0].timeout == 15
    finally:
        tmp_path.unlink()


def test_load_valid_json_config(file_config_loader: FileConfigLoader) -> None:
    """Test loading valid JSON configuration."""
    config_data = {
        "check_interval": 45,
        "sites": [{"url": "https://test.com", "timeout": 20, "content_requirements": ["Python"]}],
    }

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp_file:
        json.dump(config_data, tmp_file)
        tmp_path = Path(tmp_file.name)

    try:
        config = file_config_loader.load_config(tmp_path)

        assert isinstance(config, MonitoringConfig)
        assert config.check_interval == 45
        assert len(config.sites) == 1
        assert str(config.sites[0].url) == "https://test.com/"
        assert config.sites[0].timeout == 20
    finally:
        tmp_path.unlink()


def test_load_invalid_json_config(file_config_loader: FileConfigLoader) -> None:
    """Test loading invalid JSON configuration."""
    invalid_json = '{"check_interval": 30, "sites": [}'  # Missing closing bracket

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp_file:
        tmp_file.write(invalid_json)
        tmp_path = Path(tmp_file.name)

    try:
        with pytest.raises(InvalidJsonConfigError, match="Invalid JSON configuration"):
            file_config_loader.load_config(tmp_path)
    finally:
        tmp_path.unlink()


def test_load_config_with_global_retry(file_config_loader: FileConfigLoader) -> None:
    """Test loading configuration with global retry settings."""
    config_data = {
        "check_interval": 60,
        "retry": {
            "enabled": True,
            "max_attempts": 5,
            "strategy": "exponential",
            "base_delay_seconds": 2.0,
            "max_delay_seconds": 60.0,
            "backoff_multiplier": 1.5,
            "retry_on_status_codes": [429, 500, 502, 503, 504],
            "retry_on_timeout": True,
            "retry_on_connection_error": False,
            "jitter": True,
        },
        "sites": [{"url": "https://example.com", "timeout": 10, "content_requirements": ["Test"]}],
    }

    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as tmp_file:
        yaml.dump(config_data, tmp_file)
        tmp_path = Path(tmp_file.name)

    try:
        config = file_config_loader.load_config(tmp_path)

        assert config.global_retry_config is not None
        assert config.global_retry_config.enabled is True
        assert config.global_retry_config.max_attempts == 5
        assert config.global_retry_config.strategy == RetryStrategy.EXPONENTIAL
        assert config.global_retry_config.base_delay_seconds == 2.0
        assert config.global_retry_config.retry_on_connection_error is False

        # Site should inherit global retry config
        assert config.sites[0].retry_config.max_attempts == 5
        assert config.sites[0].retry_config.strategy == RetryStrategy.EXPONENTIAL
    finally:
        tmp_path.unlink()


def test_load_config_no_sites_error(file_config_loader: FileConfigLoader):
    """Test error when no sites are configured."""
    config_data = {"check_interval": 30, "sites": []}

    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as tmp_file:
        yaml.dump(config_data, tmp_file)
        tmp_path = Path(tmp_file.name)

    try:
        with pytest.raises(ValueError, match="No sites configured"):
            file_config_loader.load_config(tmp_path)
    finally:
        tmp_path.unlink()


def test_load_config_missing_sites_key(file_config_loader: FileConfigLoader):
    """Test error when sites key is missing."""
    config_data = {"check_interval": 30}

    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as tmp_file:
        yaml.dump(config_data, tmp_file)
        tmp_path = Path(tmp_file.name)

    try:
        with pytest.raises(ValueError, match="No sites configured"):
            file_config_loader.load_config(tmp_path)
    finally:
        tmp_path.unlink()


def test_parse_site_config_minimal(file_config_loader: FileConfigLoader):
    """Test parsing minimal site configuration."""
    site_data = {"url": "https://example.com", "content_requirements": ["Python"]}

    site_config = file_config_loader._parse_site_config(site_data)

    assert str(site_config.url) == "https://example.com/"
    assert site_config.name == "https://example.com/"
    assert site_config.timeout == 30  # Default
    assert site_config.require_all_content is True  # Default
    assert len(site_config.content_requirements) == 1
    assert isinstance(site_config.retry_config, RetryConfig)


def test_parse_site_config_complete(file_config_loader: FileConfigLoader):
    """Test parsing complete site configuration."""
    site_data = {
        "url": "https://test.com",
        "name": "Test Site",
        "timeout": 25,
        "require_all_content": False,
        "content_requirements": ["Welcome", {"pattern": "Login", "case_sensitive": False}],
    }

    site_config = file_config_loader._parse_site_config(site_data)

    assert str(site_config.url) == "https://test.com/"
    assert site_config.name == "Test Site"
    assert site_config.timeout == 25
    assert site_config.require_all_content is False
    assert len(site_config.content_requirements) == 2

    # Check content requirements
    assert site_config.content_requirements[0].pattern == "Welcome"
    assert site_config.content_requirements[1].pattern == "Login"


def test_parse_site_config_with_site_specific_retry(file_config_loader: FileConfigLoader):
    """Test parsing site configuration with site-specific retry settings."""
    global_retry = RetryConfig(
        max_attempts=3, strategy=RetryStrategy.EXPONENTIAL, base_delay_seconds=1.0
    )

    site_data = {
        "url": "https://critical.com",
        "content_requirements": ["Critical Content"],
        "retry": {"max_attempts": 10, "base_delay_seconds": 0.5, "retry_on_timeout": False},
    }

    site_config = file_config_loader._parse_site_config(site_data, global_retry)

    # Should inherit some global settings and override others
    assert site_config.retry_config.max_attempts == 10  # Overridden
    assert site_config.retry_config.base_delay_seconds == 0.5  # Overridden
    assert site_config.retry_config.retry_on_timeout is False  # Overridden
    assert site_config.retry_config.strategy == RetryStrategy.EXPONENTIAL  # Inherited
    assert site_config.retry_config.enabled is True  # Inherited


def test_parse_site_config_content_requirements_string_format(file_config_loader: FileConfigLoader):
    """Test parsing content requirements in string format."""
    site_data = {
        "url": "https://example.com",
        "content_requirements": ["Hello", "World", "Test"],
    }

    site_config = file_config_loader._parse_site_config(site_data)

    assert len(site_config.content_requirements) == 3
    assert all(isinstance(req, ContentRequirement) for req in site_config.content_requirements)
    assert site_config.content_requirements[0].pattern == "Hello"
    assert site_config.content_requirements[1].pattern == "World"
    assert site_config.content_requirements[2].pattern == "Test"


def test_parse_site_config_content_requirements_dict_format(file_config_loader: FileConfigLoader):
    """Test parsing content requirements in dictionary format."""
    site_data = {
        "url": "https://example.com",
        "content_requirements": [
            {"pattern": "Login", "case_sensitive": True},
            {"pattern": "dashboard", "case_sensitive": False},
        ],
    }

    site_config = file_config_loader._parse_site_config(site_data)

    assert len(site_config.content_requirements) == 2
    assert site_config.content_requirements[0].pattern == "Login"
    assert site_config.content_requirements[1].pattern == "dashboard"


def test_parse_site_config_mixed_content_requirements(file_config_loader: FileConfigLoader):
    """Test parsing mixed string and dictionary content requirements."""
    site_data = {
        "url": "https://example.com",
        "content_requirements": [
            "Simple string",
            {"pattern": "Complex pattern", "case_sensitive": False},
        ],
    }

    site_config = file_config_loader._parse_site_config(site_data)

    assert len(site_config.content_requirements) == 2
    assert site_config.content_requirements[0].pattern == "Simple string"
    assert site_config.content_requirements[1].pattern == "Complex pattern"


def test_parse_retry_config_minimal(file_config_loader: FileConfigLoader):
    """Test parsing minimal retry configuration."""
    retry_data = {}

    retry_config = file_config_loader._parse_retry_config(retry_data)

    # Should use all defaults
    assert retry_config.enabled is True
    assert retry_config.max_attempts == 3
    assert retry_config.strategy == RetryStrategy.EXPONENTIAL
    assert retry_config.base_delay_seconds == 1.0
    assert retry_config.max_delay_seconds == 30.0
    assert retry_config.backoff_multiplier == 2.0
    assert retry_config.retry_on_status_codes == [500, 502, 503, 504, 429]
    assert retry_config.retry_on_timeout is True
    assert retry_config.retry_on_connection_error is True
    assert retry_config.jitter is True


def test_parse_retry_config_complete(file_config_loader: FileConfigLoader):
    """Test parsing complete retry configuration."""
    retry_data = {
        "enabled": False,
        "max_attempts": 5,
        "strategy": "linear",
        "base_delay_seconds": 2.5,
        "max_delay_seconds": 120.0,
        "backoff_multiplier": 1.5,
        "retry_on_status_codes": [429, 500, 502],
        "retry_on_timeout": False,
        "retry_on_connection_error": False,
        "jitter": False,
    }

    retry_config = file_config_loader._parse_retry_config(retry_data)

    assert retry_config.enabled is False
    assert retry_config.max_attempts == 5
    assert retry_config.strategy == RetryStrategy.LINEAR
    assert retry_config.base_delay_seconds == 2.5
    assert retry_config.max_delay_seconds == 120.0
    assert retry_config.backoff_multiplier == 1.5
    assert retry_config.retry_on_status_codes == [429, 500, 502]
    assert retry_config.retry_on_timeout is False
    assert retry_config.retry_on_connection_error is False
    assert retry_config.jitter is False


def test_parse_retry_config_strategy_case_insensitive(file_config_loader: FileConfigLoader):
    """Test that retry strategy parsing is case insensitive."""
    test_cases = [
        ("exponential", RetryStrategy.EXPONENTIAL),
        ("EXPONENTIAL", RetryStrategy.EXPONENTIAL),
        ("Exponential", RetryStrategy.EXPONENTIAL),
        ("linear", RetryStrategy.LINEAR),
        ("LINEAR", RetryStrategy.LINEAR),
        ("fixed", RetryStrategy.FIXED),
        ("FIXED", RetryStrategy.FIXED),
    ]

    for strategy_str, expected_strategy in test_cases:
        retry_data = {"strategy": strategy_str}
        retry_config = file_config_loader._parse_retry_config(retry_data)
        assert retry_config.strategy == expected_strategy


def test_parse_retry_config_invalid_strategy(file_config_loader: FileConfigLoader):
    """Test error handling for invalid retry strategy."""
    retry_data = {"strategy": "invalid_strategy"}

    with pytest.raises(InvalidRetryStrategyError, match="Invalid retry strategy: invalid_strategy"):
        file_config_loader._parse_retry_config(retry_data)


def test_parse_retry_config_partial_override(file_config_loader: FileConfigLoader):
    """Test parsing retry configuration with partial overrides."""
    retry_data = {"max_attempts": 7, "base_delay_seconds": 3.0, "retry_on_timeout": False}

    retry_config = file_config_loader._parse_retry_config(retry_data)

    # Overridden values
    assert retry_config.max_attempts == 7
    assert retry_config.base_delay_seconds == 3.0
    assert retry_config.retry_on_timeout is False

    # Default values
    assert retry_config.enabled is True
    assert retry_config.strategy == RetryStrategy.EXPONENTIAL
    assert retry_config.max_delay_seconds == 30.0


def test_load_complex_config_yaml(file_config_loader: FileConfigLoader):
    """Test loading complex configuration from YAML."""
    config_data = {
        "check_interval": 45,
        "log_file": "monitoring.log",
        "retry": {
            "enabled": True,
            "max_attempts": 4,
            "strategy": "exponential",
            "base_delay_seconds": 1.5,
            "retry_on_status_codes": [429, 500, 502, 503, 504],
        },
        "sites": [
            {
                "url": "https://api.example.com",
                "name": "API Endpoint",
                "timeout": 10,
                "content_requirements": ["API", "v1"],
                "require_all_content": True,
            },
            {
                "url": "https://web.example.com",
                "name": "Web Interface",
                "timeout": 20,
                "content_requirements": [{"pattern": "Welcome", "case_sensitive": False}],
                "retry": {"max_attempts": 6, "strategy": "linear"},
            },
        ],
    }

    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as tmp_file:
        yaml.dump(config_data, tmp_file)
        tmp_path = Path(tmp_file.name)

    try:
        config = file_config_loader.load_config(tmp_path)

        # Verify main config
        assert config.check_interval == 45
        assert config.log_file == "monitoring.log"
        assert config.global_retry_config is not None
        assert config.global_retry_config.max_attempts == 4

        # Verify first site
        site1 = config.sites[0]
        assert str(site1.url) == "https://api.example.com/"
        assert site1.name == "API Endpoint"
        assert site1.timeout == 10
        assert len(site1.content_requirements) == 2
        assert site1.require_all_content is True
        # Should inherit global retry config
        assert site1.retry_config.max_attempts == 4
        assert site1.retry_config.strategy == RetryStrategy.EXPONENTIAL

        # Verify second site
        site2 = config.sites[1]
        assert str(site2.url) == "https://web.example.com/"
        assert site2.name == "Web Interface"
        assert site2.timeout == 20
        assert len(site2.content_requirements) == 1
        # Should have overridden retry config
        assert site2.retry_config.max_attempts == 6
        assert site2.retry_config.strategy == RetryStrategy.LINEAR
        # But inherit other settings
        assert site2.retry_config.base_delay_seconds == 1.5

    finally:
        tmp_path.unlink()


def test_load_config_yml_extension(file_config_loader: FileConfigLoader):
    """Test loading configuration from .yml file."""
    config_data = {
        "check_interval": 30,
        "sites": [{"url": "https://example.com", "content_requirements": ["Test"]}],
    }

    with tempfile.NamedTemporaryFile(suffix=".yml", mode="w", delete=False) as tmp_file:
        yaml.dump(config_data, tmp_file)
        tmp_path = Path(tmp_file.name)

    try:
        config = file_config_loader.load_config(tmp_path)
        assert isinstance(config, MonitoringConfig)
        assert config.check_interval == 30
    finally:
        tmp_path.unlink()


def test_load_config_with_defaults(file_config_loader: FileConfigLoader):
    """Test loading configuration that relies on default values."""
    config_data = {"sites": [{"url": "https://minimal.com", "content_requirements": ["Minimal"]}]}

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp_file:
        json.dump(config_data, tmp_file)
        tmp_path = Path(tmp_file.name)

    try:
        config = file_config_loader.load_config(tmp_path)

        # Should use defaults
        assert config.check_interval == 60
        assert config.log_file == "site_guard.log"
        assert config.global_retry_config is None

        site = config.sites[0]
        assert str(site.url) == "https://minimal.com/"
        assert site.name == "https://minimal.com/"
        assert site.timeout == 30
        assert site.require_all_content is True
        assert len(site.content_requirements) == 1

    finally:
        tmp_path.unlink()


@patch("pathlib.Path.exists")
def test_load_config_file_not_found_mocked(mock_exists, file_config_loader: FileConfigLoader):
    """Test file not found error with mocked path."""
    mock_exists.return_value = False

    config_path = Path("/fake/config.yaml")

    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        file_config_loader.load_config(config_path)


@patch("pathlib.Path.read_text")
@patch("pathlib.Path.exists")
def test_load_config_yaml_parse_error(
    mock_exists, mock_read_text, file_config_loader: FileConfigLoader
):
    """Test YAML parsing error."""
    mock_exists.return_value = True
    mock_read_text.return_value = "invalid: yaml: content: ["

    config_path = Path("/fake/config.yaml")

    # YAML parsing error should be propagated
    with pytest.raises(Exception):  # yaml.YAMLError or similar
        file_config_loader.load_config(config_path)


def test_parse_config_validation_error(file_config_loader: FileConfigLoader):
    """Test Pydantic validation error handling."""
    # Missing required URL field
    config_data = {"sites": [{"name": "Missing URL"}]}

    with pytest.raises(Exception):  # Should raise validation error
        file_config_loader._parse_config(config_data)


def test_parse_retry_config_invalid_strategy_detailed(file_config_loader: FileConfigLoader):
    """Test detailed error message for invalid retry strategy."""
    retry_data = {"strategy": "unknown_strategy"}

    with pytest.raises(InvalidRetryStrategyError) as exc_info:
        file_config_loader._parse_retry_config(retry_data)

    error_message = str(exc_info.value)
    assert "Invalid retry strategy: unknown_strategy" in error_message
    assert "EXPONENTIAL" in error_message
    assert "LINEAR" in error_message
    assert "FIXED" in error_message


def test_parse_site_config_invalid_content_requirement_type(file_config_loader: FileConfigLoader):
    """Test error handling for invalid content requirement types."""
    site_data = {
        "url": "https://example.com",
        "content_requirements": [123, True],  # Invalid types
    }

    # Should handle gracefully or raise appropriate error
    # The exact behavior depends on ContentRequirement implementation
    with pytest.raises(Exception):
        file_config_loader._parse_site_config(site_data)


def test_load_config_empty_file(file_config_loader: FileConfigLoader):
    """Test loading empty configuration file."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as tmp_file:
        tmp_file.write("")
        tmp_path = Path(tmp_file.name)

    try:
        with pytest.raises(Exception):  # Should fail due to missing sites
            file_config_loader.load_config(tmp_path)
    finally:
        tmp_path.unlink()


def test_load_config_null_content(file_config_loader: FileConfigLoader):
    """Test loading configuration file with null content."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as tmp_file:
        tmp_file.write("null")
        tmp_path = Path(tmp_file.name)

    try:
        with pytest.raises(Exception):  # Should fail
            file_config_loader.load_config(tmp_path)
    finally:
        tmp_path.unlink()


def test_parse_site_config_empty_content_requirements(file_config_loader: FileConfigLoader):
    """Test parsing site with empty content requirements list."""
    site_data = {"url": "https://example.com", "content_requirements": []}

    with pytest.raises(ValidationError):
        file_config_loader._parse_site_config(site_data)


def test_parse_retry_config_empty_status_codes(file_config_loader: FileConfigLoader):
    """Test parsing retry config with empty status codes list."""
    retry_data = {"retry_on_status_codes": []}

    retry_config = file_config_loader._parse_retry_config(retry_data)

    assert retry_config.retry_on_status_codes == []


def test_load_config_case_insensitive_file_extensions(file_config_loader: FileConfigLoader):
    """Test that file extension matching is case insensitive."""
    config_data = {"sites": [{"url": "https://example.com", "content_requirements": ["Test"]}]}

    extensions = [".YAML", ".YML", ".JSON"]

    for ext in extensions:
        with tempfile.NamedTemporaryFile(suffix=ext, mode="w", delete=False) as tmp_file:
            if ext == ".JSON":
                json.dump(config_data, tmp_file)
            else:
                yaml.dump(config_data, tmp_file)
            tmp_path = Path(tmp_file.name)

        try:
            config = file_config_loader.load_config(tmp_path)
            assert isinstance(config, MonitoringConfig)
        finally:
            tmp_path.unlink()
