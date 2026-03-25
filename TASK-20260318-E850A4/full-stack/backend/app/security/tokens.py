from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

from app.core.config import settings
from app.core.errors import unauthorized


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, role: str) -> str:
    now = _utcnow()
    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_access_exp_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_access_secret, algorithm="HS256")


def create_refresh_token(subject: str, role: str) -> str:
    now = _utcnow()
    payload = {
        "sub": subject,
        "role": role,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_refresh_exp_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_refresh_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_access_secret, algorithms=["HS256"])
    except InvalidTokenError as exc:
        raise unauthorized("Invalid access token") from exc


def decode_refresh_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_refresh_secret, algorithms=["HS256"])
    except InvalidTokenError as exc:
        raise unauthorized("Invalid refresh token") from exc
