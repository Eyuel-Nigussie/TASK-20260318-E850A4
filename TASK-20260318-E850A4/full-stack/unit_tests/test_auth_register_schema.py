from pydantic import ValidationError

from app.schemas.auth import RegisterRequest


def test_register_request_validates_email():
    try:
        RegisterRequest(email="invalid_email", password="StrongPass1!", confirm_password="StrongPass1!")
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for invalid email")


def test_register_request_accepts_valid_payload():
    payload = RegisterRequest(email="user@example.com", password="StrongPass1!", confirm_password="StrongPass1!")
    assert payload.email == "user@example.com"
