from collections.abc import Sequence
from typing import Self

from pydantic import (
    BaseModel,
    HttpUrl,
    NonNegativeFloat,
    StrictBool,
    field_serializer,
    field_validator,
)

from site_guard.domain.models.content import ContentRequirement


class SiteConfigResult(BaseModel):
    """Result of checking a site configuration."""

    success: StrictBool
    failed_patterns: Sequence[str] = []  # Patterns that did not match

    model_config = {"frozen": True}


class SiteConfig(BaseModel):
    """Configuration for a single site to monitor."""

    url: HttpUrl
    content_requirements: Sequence[ContentRequirement | str]  # Support both old and new format
    timeout: NonNegativeFloat = 30
    require_all_content: StrictBool = True  # If False, only one requirement needs to match
    model_config = {"frozen": True}

    @field_validator("content_requirements")
    @classmethod
    def validate_content_requirements(
        cls, v: Sequence[ContentRequirement | str]
    ) -> list[ContentRequirement]:
        if not v:
            raise ValueError("At least one content requirement must be specified")

        requirements = []
        for req in v:
            if isinstance(req, str):
                # Convert string to ContentRequirement for backward compatibility
                requirements.append(ContentRequirement(pattern=req))
            else:
                requirements.append(req)

        return requirements

    @field_serializer("url")
    def serialize_dt(self, url: HttpUrl) -> str:
        return str(url)

    def check_content_requirements(self, content: str) -> SiteConfigResult:
        """
        Check if content meets the requirements.

        Returns:
            tuple: (success: bool, failed_patterns: list[str])
        """
        failed_patterns = []

        for req in self.content_requirements:
            # If it's a string, treat it as a simple substring match
            if isinstance(req, str) and req not in content:
                failed_patterns.append(req)
                continue
            if isinstance(req, ContentRequirement) and not req.matches(content):
                failed_patterns.append(req.pattern)

        if self.require_all_content:
            # All requirements must pass
            success = len(failed_patterns) == 0
        else:
            # At least one requirement must pass
            success = len(failed_patterns) < len(self.content_requirements)

        return SiteConfigResult(success=success, failed_patterns=failed_patterns)


class MonitoringConfig(BaseModel):
    """Overall monitoring configuration."""

    model_config = {"frozen": True}

    check_interval: NonNegativeFloat = 60  # seconds
    sites: list[SiteConfig]
    log_file: str = "site_guard.log"

    @field_validator("check_interval")
    @classmethod
    def validate_check_interval(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Check interval must be positive")
        return v

    def with_overridden_interval(self, interval: float) -> Self:
        """Create a new config with an overridden check interval."""
        if not isinstance(interval, int) or interval < 0:
            raise ValueError("Overridden interval must be positive integer")
        return self.model_copy(update={"check_interval": interval})
