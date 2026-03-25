from datetime import datetime, timedelta, timezone

from app.services.registration_service import _utc_now


def test_utc_now_timezone_aware():
    now = _utc_now()
    assert now.tzinfo is not None


def test_within_72h_boundary_logic_example():
    now = datetime.now(timezone.utc)
    submitted_at = now - timedelta(hours=71, minutes=59)
    assert now <= submitted_at + timedelta(hours=72)


def test_outside_72h_boundary_logic_example():
    now = datetime.now(timezone.utc)
    submitted_at = now - timedelta(hours=72, minutes=1)
    assert not (now <= submitted_at + timedelta(hours=72))
