from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models.activity import Activity
from app.models.funding_transaction import FundingTransaction
from app.models.quality_validation_result import QualityValidationResult
from app.models.registration_form import RegistrationForm
from app.services.audit_service import AuditService


class QualityService:
    def __init__(self, db: Session):
        self.db = db

    def compute(self, *, activity_id: int) -> dict:
        activity = (
            self.db.execute(
                select(Activity).where(Activity.id == activity_id).where(Activity.deleted_at.is_(None)).limit(1)
            )
            .scalar_one_or_none()
        )
        if activity is None:
            raise not_found("Activity not found")

        total = (
            self.db.execute(
                select(func.count(RegistrationForm.id))
                .where(RegistrationForm.activity_id == activity_id)
                .where(RegistrationForm.deleted_at.is_(None))
            )
            .scalar_one()
        )
        approved = (
            self.db.execute(
                select(func.count(RegistrationForm.id))
                .where(RegistrationForm.activity_id == activity_id)
                .where(RegistrationForm.status == "APPROVED")
                .where(RegistrationForm.deleted_at.is_(None))
            )
            .scalar_one()
        )
        corrected = (
            self.db.execute(
                select(func.count(RegistrationForm.id))
                .where(RegistrationForm.activity_id == activity_id)
                .where(RegistrationForm.status == "SUPPLEMENTED")
                .where(RegistrationForm.deleted_at.is_(None))
            )
            .scalar_one()
        )

        confirmed_expense = (
            self.db.execute(
                select(func.coalesce(func.sum(FundingTransaction.amount), 0))
                .where(FundingTransaction.activity_id == activity_id)
                .where(FundingTransaction.tx_type == "EXPENSE")
                .where(FundingTransaction.tx_status == "CONFIRMED")
                .where(FundingTransaction.deleted_at.is_(None))
            )
            .scalar_one()
        )

        total_float = float(total)
        approval_rate = float(approved) / total_float if total_float > 0 else 0.0
        correction_rate = float(corrected) / total_float if total_float > 0 else 0.0
        overspending_rate = (float(confirmed_expense) / float(activity.budget_total)) if float(activity.budget_total) > 0 else 0.0

        payload = {
            "total_applications": int(total),
            "approved_count": int(approved),
            "corrected_count": int(corrected),
            "confirmed_expense": float(confirmed_expense),
            "budget_total": float(activity.budget_total),
        }
        row = QualityValidationResult(
            activity_id=activity_id,
            collected_at=datetime.utcnow(),
            approval_rate=approval_rate,
            correction_rate=correction_rate,
            overspending_rate=overspending_rate,
            metrics_payload=payload,
        )
        self.db.add(row)

        alert_triggered = approval_rate < 0.5 or correction_rate > 0.4 or overspending_rate > 1.10
        if alert_triggered:
            AuditService(self.db).write(
                actor_user_id=None,
                actor_username=None,
                actor_role_code=None,
                action="QUALITY_THRESHOLD_ALERT",
                entity_type="ACTIVITY",
                entity_id=str(activity_id),
                request_id=None,
                ip_address=None,
                result="SUCCESS",
                error_code=None,
                before_snapshot=None,
                after_snapshot={
                    "activity_id": activity_id,
                    "approval_rate": approval_rate,
                    "correction_rate": correction_rate,
                    "overspending_rate": overspending_rate,
                },
            )
        self.db.commit()
        self.db.refresh(row)

        return {
            "id": row.id,
            "activity_id": row.activity_id,
            "approval_rate": float(row.approval_rate),
            "correction_rate": float(row.correction_rate),
            "overspending_rate": float(row.overspending_rate),
            "metrics_payload": row.metrics_payload,
            "collected_at": row.collected_at.isoformat() if row.collected_at else None,
        }

    def list_results(self, *, activity_id: int, page: int, page_size: int) -> dict:
        rows = (
            self.db.execute(
                select(QualityValidationResult)
                .where(QualityValidationResult.activity_id == activity_id)
                .order_by(QualityValidationResult.collected_at.desc())
            )
            .scalars()
            .all()
        )
        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        page_rows = rows[start:end]
        data = [
            {
                "id": row.id,
                "activity_id": row.activity_id,
                "approval_rate": float(row.approval_rate),
                "correction_rate": float(row.correction_rate),
                "overspending_rate": float(row.overspending_rate),
                "metrics_payload": row.metrics_payload,
                "collected_at": row.collected_at.isoformat() if row.collected_at else None,
            }
            for row in page_rows
        ]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return {"items": data, "page": page, "page_size": page_size, "total": total, "total_pages": total_pages}

    def latest(self, *, activity_id: int) -> dict:
        row = (
            self.db.execute(
                select(QualityValidationResult)
                .where(QualityValidationResult.activity_id == activity_id)
                .order_by(QualityValidationResult.collected_at.desc())
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if row is None:
            raise not_found("No quality metrics found for activity")

        return {
            "id": row.id,
            "activity_id": row.activity_id,
            "approval_rate": float(row.approval_rate),
            "correction_rate": float(row.correction_rate),
            "overspending_rate": float(row.overspending_rate),
            "metrics_payload": row.metrics_payload,
            "collected_at": row.collected_at.isoformat() if row.collected_at else None,
        }
