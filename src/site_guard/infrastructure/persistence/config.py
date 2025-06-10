"""Configuration loading implementation."""

import json
from pathlib import Path
from typing import Any

import yaml
from loguru import logger
from pydantic import ValidationError

from site_guard.domain.models.config import (
    MonitoringConfig,
    RetryConfig,
    RetryStrategy,
    SiteConfig,
)
from site_guard.domain.models.content import ContentRequirement
from site_guard.domain.repositories.config import ConfigLoader


class InvalidJsonConfigError(Exception):
    """Custom exception for invalid JSON configuration files."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidFileFormatError(Exception):
    """Custom exception for unsupported file formats."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidRetryStrategyError(Exception):
    """Custom exception for invalid retry strategy in configuration."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


type TJsonData = dict[str, Any]


class FileConfigLoader(ConfigLoader):
    """File-based configuration repository."""

    def load_config(self, config_path: Path) -> MonitoringConfig:
        """Load configuration from YAML or JSON file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        content = config_path.read_text(encoding="utf-8")
        if not content.strip():
            raise ValueError(f"Configuration file is empty: {config_path}")
        match config_path.suffix.lower():
            case ".yaml" | ".yml":
                data = yaml.safe_load(content)
            case ".json":
                try:
                    data = json.loads(content)
                except (json.JSONDecodeError, TypeError) as e:
                    raise InvalidJsonConfigError(
                        f"Invalid JSON configuration: {e}. Please check your config file"
                    ) from e
            case _:
                raise InvalidFileFormatError(
                    f"Unsupported configuration file format: {config_path.suffix}. "
                    "Supported formats are .yaml, .yml, and .json."
                )
        if not isinstance(data, dict) or not data:
            raise ValueError(
                f"Configuration file is empty or invalid: {config_path}. Please check your config file."
            )
        try:
            return self._parse_config(data)
        except (ValidationError, ValueError) as e:
            logger.error(f"Configuration validation error:\n{e}. Please check your config file.")
            raise

    def _parse_config(self, config_data: TJsonData) -> MonitoringConfig:
        """Parse raw configuration data into MonitoringConfig."""

        # Parse global retry configuration
        global_retry_config = None
        if "retry" in config_data:
            global_retry_config = self._parse_retry_config(config_data["retry"])

        # Parse sites
        sites = []
        for site_data in config_data.get("sites", []):
            site_config = self._parse_site_config(site_data, global_retry_config)
            sites.append(site_config)

        if not sites:
            raise ValueError("No sites configured")

        return MonitoringConfig(
            check_interval=config_data.get("check_interval", 60),
            sites=sites,
            log_file=config_data.get("log_file", "site_guard.log"),
            global_retry_config=global_retry_config,
        )

    def _parse_site_config(
        self, site_data: TJsonData, global_retry: RetryConfig | None = None
    ) -> SiteConfig:
        """Parse site configuration."""

        # Parse content requirements
        content_requirements = []
        if "content_requirements" in site_data:
            for req in site_data["content_requirements"]:
                if isinstance(req, str):
                    content_requirements.append(ContentRequirement(pattern=req))
                elif isinstance(req, dict):
                    content_requirements.append(ContentRequirement(**req))

        # Parse site-specific retry configuration
        retry_config = global_retry or RetryConfig()
        if "retry" in site_data:
            site_retry_data = site_data["retry"]
            # If global retry exists, use it as base and override with site-specific values
            if global_retry:
                retry_dict = {
                    "enabled": global_retry.enabled,
                    "max_attempts": global_retry.max_attempts,
                    "strategy": global_retry.strategy.value,
                    "base_delay_seconds": global_retry.base_delay_seconds,
                    "max_delay_seconds": global_retry.max_delay_seconds,
                    "backoff_multiplier": global_retry.backoff_multiplier,
                    "retry_on_status_codes": global_retry.retry_on_status_codes.copy(),
                    "retry_on_timeout": global_retry.retry_on_timeout,
                    "retry_on_connection_error": global_retry.retry_on_connection_error,
                    "jitter": global_retry.jitter,
                }
                retry_dict.update(site_retry_data)
                retry_config = self._parse_retry_config(retry_dict)
            else:
                retry_config = self._parse_retry_config(site_retry_data)

        return SiteConfig(
            url=site_data["url"],
            name=site_data.get("name"),
            content_requirements=content_requirements,
            timeout=site_data.get("timeout", 30),
            require_all_content=site_data.get("require_all_content", True),
            retry_config=retry_config,
        )

    def _parse_retry_config(self, retry_data: TJsonData) -> RetryConfig:
        """Parse retry configuration."""

        # Parse strategy enum
        strategy_str = retry_data.get("strategy", "exponential").lower()
        try:
            strategy = RetryStrategy(strategy_str.upper())
        except ValueError as e:
            raise InvalidRetryStrategyError(
                f"Invalid retry strategy: {strategy_str}. Possible values are: {', '.join(s.value for s in RetryStrategy)}"
            ) from e

        return RetryConfig(
            enabled=retry_data.get("enabled", True),
            max_attempts=retry_data.get("max_attempts", 3),
            strategy=strategy,
            base_delay_seconds=retry_data.get("base_delay_seconds", 1.0),
            max_delay_seconds=retry_data.get("max_delay_seconds", 30.0),
            backoff_multiplier=retry_data.get("backoff_multiplier", 2.0),
            retry_on_status_codes=retry_data.get(
                "retry_on_status_codes", [500, 502, 503, 504, 429]
            ),
            retry_on_timeout=retry_data.get("retry_on_timeout", True),
            retry_on_connection_error=retry_data.get("retry_on_connection_error", True),
            jitter=retry_data.get("jitter", True),
        )
