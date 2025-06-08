from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel, HttpUrl, NonNegativeInt, field_serializer

from site_guard.domain.models.status import CheckStatus


class SiteCheckResult(BaseModel):
    """Result of a site availability check."""

    url: HttpUrl
    status: CheckStatus
    response_time_ms: NonNegativeInt | None
    timestamp: datetime
    error_message: str | None = None
    failed_content_requirements: Sequence[str] | None = None

    model_config = {"frozen": True}

    @property
    def is_success(self) -> bool:
        """Check if the result indicates success."""
        return self.status == CheckStatus.SUCCESS

    @property
    def is_connection_error(self) -> bool:
        """Check if the result indicates a connection error."""
        return self.status == CheckStatus.CONNECTION_ERROR

    @property
    def is_content_error(self) -> bool:
        """Check if the result indicates a content error."""
        return self.status == CheckStatus.CONTENT_ERROR

    @field_serializer("url")
    def serialize_dt(self, url: HttpUrl) -> str:
        return str(url)
