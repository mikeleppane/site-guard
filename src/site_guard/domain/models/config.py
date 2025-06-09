from collections.abc import Sequence
from enum import StrEnum

from pydantic import (
    BaseModel,
    HttpUrl,
    NonNegativeFloat,
    PositiveFloat,
    PositiveInt,
    StrictBool,
    field_serializer,
)
from pydantic.dataclasses import Field as DField
from pydantic.dataclasses import dataclass

from site_guard.domain.models.content import ContentRequirement


class RetryStrategy(StrEnum):
    """Retry strategy options."""

    FIXED = "FIXED"
    EXPONENTIAL = "EXPONENTIAL"
    LINEAR = "LINEAR"


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for HTTP retry mechanism."""

    enabled: StrictBool = True
    max_attempts: PositiveInt = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay_seconds: NonNegativeFloat = 1.0
    max_delay_seconds: NonNegativeFloat = 30.0
    backoff_multiplier: PositiveFloat = 2.0
    retry_on_status_codes: list[int] = DField(
        default_factory=lambda: [500, 502, 503, 504]
    )  # Common server errors
    retry_on_timeout: StrictBool = True
    retry_on_connection_error: StrictBool = True
    jitter: StrictBool = True

    def __post_init__(self) -> None:
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds must be >= base_delay_seconds")

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        if attempt <= 0:
            return 0.0

        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay_seconds
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay_seconds * attempt
        else:  # EXPONENTIAL
            delay = self.base_delay_seconds * (self.backoff_multiplier ** (attempt - 1))

        # Apply maximum delay limit
        delay = min(delay, self.max_delay_seconds)

        # Add jitter if enabled
        if self.jitter:
            import random

            jitter_factor = random.uniform(0.8, 1.2)  # noqa: S311
            delay *= jitter_factor

        return delay


class SiteConfigResult(BaseModel):
    """Result of checking a site configuration."""

    success: StrictBool
    failed_patterns: Sequence[str] = []  # Patterns that did not match

    model_config = {"frozen": True}


@dataclass
class SiteConfig:
    """Configuration for a single site to monitor."""

    url: HttpUrl
    content_requirements: Sequence[ContentRequirement | str]  # Support both old and new format
    timeout: NonNegativeFloat = 30
    require_all_content: StrictBool = True  # If False, only one requirement needs to match
    name: str | None = None
    retry_config: RetryConfig = DField(default_factory=lambda: RetryConfig())

    @field_serializer("url")
    def serialize_dt(self, url: HttpUrl) -> str:
        return str(url)

    def __post_init__(self) -> None:
        if self.name is None:
            self.name = str(self.url)
        if not self.content_requirements:
            raise ValueError("At least one content requirement must be specified")
        reqs = []
        for req in self.content_requirements:
            if isinstance(req, str):
                # Convert string to ContentRequirement for backward compatibility
                reqs.append(ContentRequirement(pattern=req))
            else:
                reqs.append(req)
        self.content_requirements = reqs

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


@dataclass
class MonitoringConfig:
    """Overall monitoring configuration."""

    sites: list[SiteConfig]
    check_interval: NonNegativeFloat = 60  # seconds
    log_file: str = "site_guard.log"
    global_retry_config: RetryConfig | None = None

    def __post_init__(self) -> None:
        if self.global_retry_config:
            for site in self.sites:
                if site.retry_config == RetryConfig():  # Default retry config
                    site.retry_config = self.global_retry_config

    def with_overridden_interval(self, interval: float) -> "MonitoringConfig":
        """Create a new config with an overridden check interval."""
        if not isinstance(interval, int) or interval < 0:
            raise ValueError("Overridden interval must be positive integer")
        return MonitoringConfig(
            sites=self.sites,
            check_interval=interval,
            log_file=self.log_file,
            global_retry_config=self.global_retry_config,
        )
