import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from site_guard.domain.models.config import MonitoringConfig
from site_guard.infrastructure.persistence.config import (
    FileConfigLoader,
    InvalidJsonConfigError,
)


@pytest.mark.asyncio
async def test_file_config_loader_with_valid_yaml() -> None:
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


@pytest.mark.asyncio
async def test_file_config_loader_with_valid_json() -> None:
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


@pytest.mark.asyncio
async def test_file_config_loader_with_invalid_json() -> None:
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


@pytest.mark.asyncio
async def test_file_config_loader_invalid_model_data() -> None:
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

        loader = FileConfigLoader()
        with pytest.raises(ValidationError):
            loader.load_config(temp_file)
