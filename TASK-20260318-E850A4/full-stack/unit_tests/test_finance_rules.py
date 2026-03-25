from app.services.review_service import ALLOWED_TRANSITIONS


def test_submitted_allows_waitlist():
    assert "WAITLISTED" in ALLOWED_TRANSITIONS["SUBMITTED"]


def test_promoted_is_terminal():
    assert ALLOWED_TRANSITIONS["PROMOTED"] == set()
