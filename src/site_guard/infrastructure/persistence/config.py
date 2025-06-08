"""Configuration loading implementation."""

import json
from pathlib import Path

import yaml
from loguru import logger
from pydantic import ValidationError

from site_guard.domain.models.config import MonitoringConfig
from site_guard.domain.repositories.config import ConfigLoader


class InvalidJsonConfigError(Exception):
    """Custom exception for invalid JSON configuration files."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class FileConfigLoader(ConfigLoader):
    """File-based configuration repository."""

    def load_config(self, config_path: Path) -> MonitoringConfig:
        """Load configuration from YAML or JSON file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        content = config_path.read_text(encoding="utf-8")

        if config_path.suffix.lower() in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        elif config_path.suffix.lower() == ".json":
            try:
                data = json.loads(content)
            except (json.JSONDecodeError, TypeError) as e:
                raise InvalidJsonConfigError(
                    f"Invalid JSON configuration: {e}. Please check your config file"
                ) from e
        else:
            raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
        try:
            config: MonitoringConfig = MonitoringConfig.model_validate(data)
            return config
        except ValidationError as e:
            logger.error(f"Configuration validation error:\n{e}. Please check your config file.")
            raise
