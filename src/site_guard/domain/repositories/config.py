from pathlib import Path
from typing import Protocol, runtime_checkable

from site_guard.domain.models.config import MonitoringConfig


@runtime_checkable
class ConfigLoader(Protocol):
    """Protocol for loading configuration from a file."""

    async def load_config(self, config_path: Path) -> MonitoringConfig:
        """Load configuration from the specified path."""
