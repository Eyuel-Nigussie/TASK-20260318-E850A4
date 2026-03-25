from app.services.system_service import SystemService


class DummyDB:
    pass


def test_mask_none_returns_none():
    service = SystemService(DummyDB())
    assert service._mask(None) is None


def test_mask_short_value_all_asterisks():
    service = SystemService(DummyDB())
    assert service._mask("1234") == "****"


def test_mask_long_value_last_four_visible():
    service = SystemService(DummyDB())
    assert service._mask("A123456789") == "****6789"
