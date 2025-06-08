from site_guard.domain.models.status import CheckStatus


def test_status_values() -> None:
    """Test that status enum has expected values."""
    assert CheckStatus.SUCCESS.value == "SUCCESS"
    assert CheckStatus.CONNECTION_ERROR.value == "CONNECTION_ERROR"
    assert CheckStatus.CONTENT_ERROR.value == "CONTENT_ERROR"
    assert CheckStatus.TIMEOUT_ERROR.value == "TIMEOUT_ERROR"
    assert str(CheckStatus.SUCCESS) == "SUCCESS"


def test_status_comparison() -> None:
    """Test status enum comparison."""
    assert CheckStatus.SUCCESS is CheckStatus.SUCCESS
    assert str(CheckStatus.SUCCESS) != str(CheckStatus.CONNECTION_ERROR)
