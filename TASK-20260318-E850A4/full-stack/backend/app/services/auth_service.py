from datetime import datetime

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import conflict, forbidden, unauthorized, validation_error
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth import UserInfo
from app.security.passwords import (
    generate_salt,
    hash_password,
    is_locked,
    lock_until_time,
    should_reset_failed_window,
    utc_now,
    verify_password,
)
from app.security.tokens import create_access_token, create_refresh_token, decode_refresh_token
from app.services.audit_service import AuditService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AuthRepository(db)
        self.audit = AuditService(db)

    def login(self, username: str, password: str, request: Request, request_id: str) -> dict:
        lookup = self.repo.get_user_with_role(username)
        if lookup is None:
            self.audit.write(
                actor_user_id=None,
                actor_username=username,
                actor_role_code=None,
                action="LOGIN",
                entity_type="USER",
                entity_id=username,
                request_id=request_id,
                ip_address=request.client.host if request.client else None,
                result="FAILED",
                error_code="AUTHENTICATION_FAILED",
            )
            raise unauthorized("Invalid username or password")

        user, role = lookup

        if not user.is_active:
            self.audit.write(
                actor_user_id=user.id,
                actor_username=user.username,
                actor_role_code=role.code,
                action="LOGIN",
                entity_type="USER",
                entity_id=str(user.id),
                request_id=request_id,
                ip_address=request.client.host if request.client else None,
                result="FAILED",
                error_code="FORBIDDEN",
            )
            raise forbidden("User is inactive")

        if is_locked(user.locked_until):
            self.audit.write(
                actor_user_id=user.id,
                actor_username=user.username,
                actor_role_code=role.code,
                action="LOGIN",
                entity_type="USER",
                entity_id=str(user.id),
                request_id=request_id,
                ip_address=request.client.host if request.client else None,
                result="FAILED",
                error_code="ACCOUNT_LOCKED",
            )
            raise forbidden("Account is locked")

        password_ok = verify_password(password, user.password_salt, user.password_hash)
        now = utc_now()

        if not password_ok:
            if should_reset_failed_window(user.first_failed_login_at):
                user.first_failed_login_at = now
                user.failed_login_count = 0

            user.failed_login_count += 1
            if user.failed_login_count >= settings.login_max_attempts:
                user.locked_until = lock_until_time()

            self.repo.save_user(user)
            self.audit.write(
                actor_user_id=user.id,
                actor_username=user.username,
                actor_role_code=role.code,
                action="LOGIN",
                entity_type="USER",
                entity_id=str(user.id),
                request_id=request_id,
                ip_address=request.client.host if request.client else None,
                result="FAILED",
                error_code="AUTHENTICATION_FAILED",
            )
            raise unauthorized("Invalid username or password")

        user.failed_login_count = 0
        user.first_failed_login_at = None
        user.locked_until = None
        user.updated_at = datetime.utcnow()
        self.repo.save_user(user)

        access_token = create_access_token(subject=str(user.id), role=role.code)
        refresh_token = create_refresh_token(subject=str(user.id), role=role.code)

        self.audit.write(
            actor_user_id=user.id,
            actor_username=user.username,
            actor_role_code=role.code,
            action="LOGIN",
            entity_type="USER",
            entity_id=str(user.id),
            request_id=request_id,
            ip_address=request.client.host if request.client else None,
            result="SUCCESS",
            after_snapshot={"role": role.code},
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_exp_minutes * 60,
            "user": UserInfo(id=user.id, username=user.username, role=role.code).model_dump(),
        }

    def refresh(self, refresh_token: str) -> dict:
        payload = decode_refresh_token(refresh_token)
        if payload.get("type") != "refresh":
            raise unauthorized("Invalid refresh token type")

        user_id = int(payload.get("sub"))
        lookup = self.repo.get_user_by_id_with_role(user_id)
        if lookup is None:
            raise unauthorized("Refresh token user not found")

        user, role = lookup
        if is_locked(user.locked_until):
            raise forbidden("Account is locked")
        if not user.is_active:
            raise forbidden("User is inactive")

        new_access = create_access_token(subject=str(user.id), role=role.code)
        new_refresh = create_refresh_token(subject=str(user.id), role=role.code)

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_exp_minutes * 60,
            "user": UserInfo(id=user.id, username=user.username, role=role.code).model_dump(),
        }

    def register(self, *, email: str, password: str, confirm_password: str, request: Request, request_id: str) -> dict:
        if password != confirm_password:
            raise validation_error("Password and confirm_password do not match")

        existing = self.repo.get_user_by_username(email)
        if existing is not None:
            raise conflict("CONFLICT", "Email already registered")

        role = self.repo.get_role_by_code("APPLICANT")
        if role is None:
            raise validation_error("Applicant role is not configured")

        salt = generate_salt()
        password_hash = hash_password(password, salt)
        user = self.repo.create_user(
            username=email,
            password_hash=password_hash,
            password_salt=salt,
            role_id=role.id,
        )

        access_token = create_access_token(subject=str(user.id), role=role.code)
        refresh_token = create_refresh_token(subject=str(user.id), role=role.code)

        self.audit.write(
            actor_user_id=user.id,
            actor_username=user.username,
            actor_role_code=role.code,
            action="REGISTER",
            entity_type="USER",
            entity_id=str(user.id),
            request_id=request_id,
            ip_address=request.client.host if request.client else None,
            result="SUCCESS",
            after_snapshot={"role": role.code},
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_exp_minutes * 60,
            "user": UserInfo(id=user.id, username=user.username, role=role.code).model_dump(),
        }
