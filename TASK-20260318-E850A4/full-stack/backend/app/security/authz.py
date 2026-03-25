from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import forbidden, unauthorized
from app.repositories.auth_repository import AuthRepository
from app.security.tokens import decode_access_token


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if authorization is None or not authorization.startswith("Bearer "):
        raise unauthorized("Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if payload.get("type") != "access":
        raise unauthorized("Invalid access token type")

    subject = payload.get("sub")
    if subject is None:
        raise unauthorized("Invalid token subject")

    repo = AuthRepository(db)
    lookup = repo.get_user_by_id_with_role(int(subject))
    if lookup is None:
        raise unauthorized("User not found")

    user, role = lookup
    if not user.is_active:
        raise forbidden("User is inactive")

    return {"user": user, "role": role}
