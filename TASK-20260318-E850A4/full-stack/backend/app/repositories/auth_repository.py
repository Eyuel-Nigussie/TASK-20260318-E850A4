from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.user import User


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_with_role(self, username: str) -> tuple[User, Role] | None:
        stmt = (
            select(User, Role)
            .join(Role, Role.id == User.role_id)
            .where(User.username == username)
            .where(User.deleted_at.is_(None))
            .limit(1)
        )
        result = self.db.execute(stmt).first()
        if result is None:
            return None
        return result[0], result[1]

    def get_user_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username).where(User.deleted_at.is_(None)).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_role_by_code(self, code: str) -> Role | None:
        stmt = select(Role).where(Role.code == code).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()

    def create_user(self, *, username: str, password_hash: str, password_salt: str, role_id: int) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            password_salt=password_salt,
            role_id=role_id,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_id_with_role(self, user_id: int) -> tuple[User, Role] | None:
        stmt = (
            select(User, Role)
            .join(Role, Role.id == User.role_id)
            .where(User.id == user_id)
            .where(User.deleted_at.is_(None))
            .limit(1)
        )
        result = self.db.execute(stmt).first()
        if result is None:
            return None
        return result[0], result[1]

    def save_user(self, user: User) -> None:
        user.updated_at = datetime.utcnow()
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
