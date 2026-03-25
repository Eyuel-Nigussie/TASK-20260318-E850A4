from datetime import datetime

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def write(
        self,
        *,
        actor_user_id: int | None,
        actor_username: str | None,
        actor_role_code: str | None,
        action: str,
        entity_type: str,
        entity_id: str,
        request_id: str,
        ip_address: str | None,
        result: str,
        error_code: str | None = None,
        before_snapshot: dict | None = None,
        after_snapshot: dict | None = None,
    ) -> None:
        item = AuditLog(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            actor_role_code=actor_role_code,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id,
            ip_address=ip_address,
            result=result,
            error_code=error_code,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            created_at=datetime.utcnow(),
        )
        self.db.add(item)
        self.db.commit()
