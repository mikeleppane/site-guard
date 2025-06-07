from enum import StrEnum


class CheckStatus(StrEnum):
    """Status of a site check."""

    SUCCESS = "SUCCESS"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    CONTENT_ERROR = "CONTENT_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    SERVER_ERROR = "SERVER_ERROR"
