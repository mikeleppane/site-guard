from pydantic import BaseModel, HttpUrl, field_validator


class SiteConfig(BaseModel):
    """Configuration for a single site to monitor."""

    url: HttpUrl
    content_requirement: str
    timeout: int = 30

    model_config = {"frozen": True}

    @field_validator("content_requirement")
    @classmethod
    def validate_content_requirement(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content requirement cannot be empty")
        return v.strip()


class MonitoringConfig(BaseModel):
    """Overall monitoring configuration."""

    model_config = {"frozen": True}

    check_interval: int = 60  # seconds
    sites: list[SiteConfig]
    log_file: str = "site_guard.log"

    @field_validator("check_interval")
    @classmethod
    def validate_check_interval(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Check interval must be positive")
        return v
