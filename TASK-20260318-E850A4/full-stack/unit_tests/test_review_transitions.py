from app.services.review_service import ALLOWED_TRANSITIONS


def test_waitlisted_can_promote_or_cancel_only():
    assert ALLOWED_TRANSITIONS["WAITLISTED"] == {"PROMOTED", "CANCELED"}


def test_approved_is_terminal():
    assert ALLOWED_TRANSITIONS["APPROVED"] == set()


def test_draft_allows_only_submitted():
    assert ALLOWED_TRANSITIONS["DRAFT"] == {"SUBMITTED"}


def test_submitted_to_approved_allowed():
    assert "APPROVED" in ALLOWED_TRANSITIONS["SUBMITTED"]
