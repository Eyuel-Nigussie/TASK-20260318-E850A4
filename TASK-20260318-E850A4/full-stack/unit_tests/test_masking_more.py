from app.services.system_service import SystemService


class DummyDB:
    pass


def test_mask_preserves_last_four_digits():
    service = SystemService(DummyDB())
    assert service._mask("13800001234") == "****1234"


def test_mask_handles_empty_string():
    service = SystemService(DummyDB())
    assert service._mask("") == ""
