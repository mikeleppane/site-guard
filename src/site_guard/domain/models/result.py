from datetime import datetime

from pydantic import BaseModel

from site_guard.models.status import CheckStatus


class SiteCheckResult(BaseModel):
    """Result of a site check."""

    url: str
    status: CheckStatus
    response_time_ms: int | None
    timestamp: datetime
    error_message: str | None = None

    model_config = {"frozen": True}

    @property
    def is_success(self) -> bool:
        """Check if the result indicates success."""
        return bool(self.status == CheckStatus.SUCCESS)

    @property
    def is_connection_error(self) -> bool:
        """Check if the result indicates a connection error."""
        return bool(self.status == CheckStatus.CONNECTION_ERROR)

    @property
    def is_content_error(self) -> bool:
        """Check if the result indicates a content error."""
        return bool(self.status == CheckStatus.CONTENT_ERROR)
