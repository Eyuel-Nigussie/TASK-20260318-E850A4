import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from app.core.config import settings


def generate_salt() -> str:
    return secrets.token_hex(16)


def hash_password(password: str, salt: str) -> str:
    digest = hashlib.scrypt(
        password=password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=2**14,
        r=8,
        p=1,
        dklen=64,
    )
    return base64.b64encode(digest).decode("ascii")


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    calculated = hash_password(password, salt)
    return hmac.compare_digest(calculated, password_hash)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_locked(locked_until: datetime | None) -> bool:
    if locked_until is None:
        return False
    return locked_until > utc_now()


def should_reset_failed_window(first_failed_login_at: datetime | None) -> bool:
    if first_failed_login_at is None:
        return True
    return first_failed_login_at + timedelta(minutes=settings.login_window_minutes) < utc_now()


def lock_until_time() -> datetime:
    return utc_now() + timedelta(minutes=settings.login_lock_minutes)
