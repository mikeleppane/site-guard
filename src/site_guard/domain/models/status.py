import enum


class CheckStatus(enum.Enum):
    """Status of a site check."""

    SUCCESS = "success"
    CONNECTION_ERROR = "connection_error"
    CONTENT_ERROR = "content_error"
    TIMEOUT_ERROR = "timeout_error"
