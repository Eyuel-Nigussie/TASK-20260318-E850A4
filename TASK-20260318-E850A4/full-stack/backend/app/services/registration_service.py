from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import conflict, not_found, validation_error
from app.models.activity import Activity
from app.models.registration_form import RegistrationForm


def _utc_now():
    return datetime.now(timezone.utc)


class RegistrationService:
    def __init__(self, db: Session):
        self.db = db

    def create_registration(self, *, activity_id: int, form_payload: dict, applicant_user_id: int) -> dict:
        activity = (
            self.db.execute(
                select(Activity).where(Activity.id == activity_id).where(Activity.deleted_at.is_(None)).limit(1)
            )
            .scalar_one_or_none()
        )
        if activity is None:
            raise not_found("Activity not found")

        row = RegistrationForm(
            activity_id=activity_id,
            applicant_user_id=applicant_user_id,
            form_payload=form_payload,
            status="DRAFT",
        )
        self.db.add(row)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise conflict("CONFLICT", "Registration already exists for this activity and applicant") from exc
        self.db.refresh(row)
        return self._to_payload(row)

    def list_my_registrations(self, *, applicant_user_id: int, page: int, page_size: int, activity_id: int | None, status: str | None) -> dict:
        stmt = (
            select(RegistrationForm)
            .where(RegistrationForm.applicant_user_id == applicant_user_id)
            .where(RegistrationForm.deleted_at.is_(None))
        )
        if activity_id is not None:
            stmt = stmt.where(RegistrationForm.activity_id == activity_id)
        if status:
            stmt = stmt.where(RegistrationForm.status == status)

        rows = self.db.execute(stmt.order_by(RegistrationForm.updated_at.desc())).scalars().all()
        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        page_rows = rows[start:end]
        data = [self._to_payload(row) for row in page_rows]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return {"items": data, "page": page, "page_size": page_size, "total": total, "total_pages": total_pages}

    def get_registration(self, *, registration_id: int, requester_user_id: int) -> dict:
        row = (
            self.db.execute(
                select(RegistrationForm)
                .where(RegistrationForm.id == registration_id)
                .where(RegistrationForm.deleted_at.is_(None))
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if row is None:
            raise not_found("Registration not found")

        if row.applicant_user_id != requester_user_id:
            raise validation_error("Registration does not belong to current user")

        return self._to_payload(row)

    def submit(self, *, registration_id: int, requester_user_id: int) -> dict:
        row = self._for_update(registration_id)
        if row is None:
            raise not_found("Registration not found")
        if row.applicant_user_id != requester_user_id:
            raise validation_error("Registration does not belong to current user")
        if row.status != "DRAFT":
            raise conflict("INVALID_STATE_TRANSITION", "Only DRAFT can be submitted")

        row.status = "SUBMITTED"
        row.submitted_at = _utc_now()
        row.row_version += 1
        row.updated_at = datetime.utcnow()
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_payload(row)

    def supplement(self, *, registration_id: int, requester_user_id: int, reason: str) -> dict:
        row = self._for_update(registration_id)
        if row is None:
            raise not_found("Registration not found")
        if row.applicant_user_id != requester_user_id:
            raise validation_error("Registration does not belong to current user")
        if row.supplement_used:
            raise conflict("SUPPLEMENT_ALREADY_USED", "Supplement can only be used once")

        activity = (
            self.db.execute(
                select(Activity).where(Activity.id == row.activity_id).where(Activity.deleted_at.is_(None)).limit(1)
            )
            .scalar_one_or_none()
        )
        if activity is None:
            raise not_found("Activity not found")

        now = _utc_now()
        if row.submitted_at is None:
            raise conflict("SUPPLEMENT_WINDOW_CLOSED", "Registration has not been submitted")

        submitted_at = row.submitted_at
        if submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=timezone.utc)

        within_72h = now <= (submitted_at + timedelta(hours=72))
        if not within_72h:
            raise conflict("SUPPLEMENT_WINDOW_CLOSED", "Supplement window closed: submitted_at + 72h exceeded")

        if activity.supplement_deadline is None or now > activity.supplement_deadline:
            raise conflict("SUPPLEMENT_WINDOW_CLOSED", "Supplement window closed: activity supplement_deadline exceeded")

        row.status = "SUPPLEMENTED"
        row.supplemented_at = now
        row.supplement_used = True
        row.form_payload = {**(row.form_payload or {}), "supplement_reason": reason}
        row.row_version += 1
        row.updated_at = datetime.utcnow()
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_payload(row)

    def _for_update(self, registration_id: int) -> RegistrationForm | None:
        return (
            self.db.execute(
                select(RegistrationForm)
                .where(RegistrationForm.id == registration_id)
                .where(RegistrationForm.deleted_at.is_(None))
                .with_for_update()
                .limit(1)
            )
            .scalar_one_or_none()
        )

    def _to_payload(self, row: RegistrationForm) -> dict:
        return {
            "id": row.id,
            "activity_id": row.activity_id,
            "applicant_user_id": row.applicant_user_id,
            "form_payload": row.form_payload,
            "status": row.status,
            "current_version": row.current_version,
            "total_material_size_bytes": row.total_material_size_bytes,
            "supplement_used": row.supplement_used,
            "row_version": row.row_version,
            "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
            "supplemented_at": row.supplemented_at.isoformat() if row.supplemented_at else None,
            "approved_at": row.approved_at.isoformat() if row.approved_at else None,
            "rejected_at": row.rejected_at.isoformat() if row.rejected_at else None,
            "canceled_at": row.canceled_at.isoformat() if row.canceled_at else None,
            "promoted_at": row.promoted_at.isoformat() if row.promoted_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
