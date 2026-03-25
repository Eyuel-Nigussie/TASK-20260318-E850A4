from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import conflict, not_found, validation_error
from app.models.audit_log import AuditLog
from app.models.registration_form import RegistrationForm
from app.models.review_workflow_record import ReviewWorkflowRecord

ALLOWED_TRANSITIONS = {
    "DRAFT": {"SUBMITTED"},
    "SUBMITTED": {"SUPPLEMENTED", "APPROVED", "REJECTED", "CANCELED", "WAITLISTED"},
    "SUPPLEMENTED": {"APPROVED", "REJECTED", "CANCELED", "WAITLISTED"},
    "WAITLISTED": {"PROMOTED", "CANCELED"},
    "APPROVED": set(),
    "REJECTED": set(),
    "CANCELED": set(),
    "PROMOTED": set(),
}


class ReviewService:
    def __init__(self, db: Session):
        self.db = db

    def transition(
        self,
        *,
        registration_id: int,
        to_state: str,
        action: str,
        comment: str | None,
        actor_user_id: int,
        idempotency_key: str | None,
        expected_row_version: int | None,
    ) -> dict:
        registration = (
            self.db.execute(
                select(RegistrationForm)
                .where(RegistrationForm.id == registration_id)
                .where(RegistrationForm.deleted_at.is_(None))
                .with_for_update()
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if registration is None:
            raise not_found("Registration not found")

        if expected_row_version is not None and registration.row_version != expected_row_version:
            raise conflict(
                "ROW_VERSION_CONFLICT",
                "Row version conflict",
                {"expected": expected_row_version, "actual": registration.row_version},
            )

        if idempotency_key:
            existing = (
                self.db.execute(
                    select(ReviewWorkflowRecord)
                    .where(ReviewWorkflowRecord.registration_form_id == registration_id)
                    .where(ReviewWorkflowRecord.idempotency_key == idempotency_key)
                    .limit(1)
                )
                .scalar_one_or_none()
            )
            if existing is not None:
                return {
                    "registration_id": registration.id,
                    "from_state": existing.from_state,
                    "to_state": existing.to_state,
                    "status": registration.status,
                    "row_version": registration.row_version,
                    "idempotent_replay": True,
                }

        from_state = registration.status
        allowed_targets = ALLOWED_TRANSITIONS.get(from_state, set())
        if to_state not in allowed_targets:
            raise conflict(
                "INVALID_STATE_TRANSITION",
                f"Cannot transition from {from_state} to {to_state}",
                {"from": from_state, "to": to_state},
            )

        registration.status = to_state
        registration.row_version += 1
        registration.updated_at = datetime.utcnow()

        now = datetime.utcnow()
        if to_state == "APPROVED":
            registration.approved_at = now
        elif to_state == "REJECTED":
            registration.rejected_at = now
        elif to_state == "CANCELED":
            registration.canceled_at = now
        elif to_state == "PROMOTED":
            registration.promoted_at = now
        elif to_state == "SUPPLEMENTED":
            registration.supplemented_at = now

        record = ReviewWorkflowRecord(
            registration_form_id=registration.id,
            from_state=from_state,
            to_state=to_state,
            action=action,
            comment=comment,
            actor_user_id=actor_user_id,
            idempotency_key=idempotency_key,
        )

        self.db.add(registration)
        self.db.add(record)
        self.db.add(
            AuditLog(
                actor_user_id=actor_user_id,
                actor_username=None,
                actor_role_code=None,
                action="REVIEW_TRANSITION",
                entity_type="REGISTRATION",
                entity_id=str(registration.id),
                request_id=None,
                ip_address=None,
                result="SUCCESS",
                error_code=None,
                before_snapshot={"status": from_state},
                after_snapshot={"status": to_state},
            )
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise conflict("CONFLICT", "Transition conflict detected") from exc

        return {
            "registration_id": registration.id,
            "from_state": from_state,
            "to_state": to_state,
            "status": registration.status,
            "row_version": registration.row_version,
            "idempotent_replay": False,
        }

    def batch_transition(
        self,
        *,
        items: list[dict],
        to_state: str,
        action: str,
        comment: str | None,
        actor_user_id: int,
        batch_key: str | None,
        atomic: bool,
    ) -> dict:
        if len(items) > 50:
            raise validation_error("Batch size exceeds 50 items")

        success_count = 0
        failure_count = 0
        results = []

        if atomic:
            snapshots = []
            for item in items:
                result = self.transition(
                    registration_id=item["registration_id"],
                    to_state=to_state,
                    action=action,
                    comment=comment,
                    actor_user_id=actor_user_id,
                    idempotency_key=f"{batch_key}:{item['registration_id']}:{to_state}" if batch_key else None,
                    expected_row_version=item.get("row_version"),
                )
                snapshots.append(result)
            return {
                "success_count": len(snapshots),
                "failure_count": 0,
                "results": [{"registration_id": entry["registration_id"], "status": "SUCCESS"} for entry in snapshots],
            }

        for item in items:
            registration_id = item["registration_id"]
            try:
                self.transition(
                    registration_id=registration_id,
                    to_state=to_state,
                    action=action,
                    comment=comment,
                    actor_user_id=actor_user_id,
                    idempotency_key=f"{batch_key}:{registration_id}:{to_state}" if batch_key else None,
                    expected_row_version=item.get("row_version"),
                )
                success_count += 1
                results.append({"registration_id": registration_id, "status": "SUCCESS"})
            except Exception as exc:  # noqa: BLE001
                failure_count += 1
                message = str(exc)
                code = "FAILED"
                if hasattr(exc, "detail") and isinstance(exc.detail, dict):
                    code = exc.detail.get("code", "FAILED")
                    message = exc.detail.get("message", message)
                results.append(
                    {
                        "registration_id": registration_id,
                        "status": "FAILED",
                        "error_code": code,
                        "message": message,
                    }
                )

        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results,
        }

    def logs(self, *, registration_id: int) -> dict:
        registration = (
            self.db.execute(
                select(RegistrationForm)
                .where(RegistrationForm.id == registration_id)
                .where(RegistrationForm.deleted_at.is_(None))
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if registration is None:
            raise not_found("Registration not found")

        rows = (
            self.db.execute(
                select(ReviewWorkflowRecord)
                .where(ReviewWorkflowRecord.registration_form_id == registration_id)
                .order_by(ReviewWorkflowRecord.created_at.desc())
            )
            .scalars()
            .all()
        )
        data = []
        for row in rows:
            data.append(
                {
                    "id": row.id,
                    "from_state": row.from_state,
                    "to_state": row.to_state,
                    "action": row.action,
                    "comment": row.comment,
                    "actor_user_id": row.actor_user_id,
                    "idempotency_key": row.idempotency_key,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )
        return {"registration_id": registration_id, "logs": data}

    def queue(self, *, page: int, page_size: int, activity_id: int | None, status: str | None, keyword: str | None) -> dict:
        stmt = select(RegistrationForm).where(RegistrationForm.deleted_at.is_(None))
        if activity_id is not None:
            stmt = stmt.where(RegistrationForm.activity_id == activity_id)
        if status:
            stmt = stmt.where(RegistrationForm.status == status)
        if keyword:
            stmt = stmt.where(RegistrationForm.id.cast(str).contains(keyword))

        rows = self.db.execute(stmt.order_by(RegistrationForm.updated_at.desc())).scalars().all()
        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        page_rows = rows[start:end]

        data = [
            {
                "registration_id": row.id,
                "activity_id": row.activity_id,
                "status": row.status,
                "row_version": row.row_version,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in page_rows
        ]

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return {
            "items": data,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }
