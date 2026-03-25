from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import conflict, not_found, validation_error
from app.models.activity import Activity
from app.models.audit_log import AuditLog
from app.models.file_blob import FileBlob
from app.models.funding_account import FundingAccount
from app.models.funding_transaction import FundingTransaction
from app.models.upload_session import UploadSession


class FinanceService:
    def __init__(self, db: Session):
        self.db = db

    def create_account(self, *, activity_id: int, account_code: str, name: str) -> dict:
        activity = (
            self.db.execute(
                select(Activity).where(Activity.id == activity_id).where(Activity.deleted_at.is_(None)).limit(1)
            )
            .scalar_one_or_none()
        )
        if activity is None:
            raise not_found("Activity not found")

        account = FundingAccount(
            activity_id=activity_id,
            account_code=account_code,
            name=name,
        )
        self.db.add(account)
        self.db.add(
            AuditLog(
                actor_user_id=None,
                actor_username=None,
                actor_role_code=None,
                action="CREATE_FUNDING_ACCOUNT",
                entity_type="FUNDING_ACCOUNT",
                entity_id=account_code,
                request_id=None,
                ip_address=None,
                result="SUCCESS",
                error_code=None,
                before_snapshot=None,
                after_snapshot={"activity_id": activity_id, "account_code": account_code, "name": name},
            )
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise conflict("CONFLICT", "Funding account already exists or invalid") from exc
        self.db.refresh(account)
        return {
            "id": account.id,
            "activity_id": account.activity_id,
            "account_code": account.account_code,
            "name": account.name,
        }

    def list_accounts(self, *, activity_id: int | None, page: int, page_size: int) -> dict:
        stmt = select(FundingAccount).where(FundingAccount.deleted_at.is_(None))
        if activity_id is not None:
            stmt = stmt.where(FundingAccount.activity_id == activity_id)

        rows = self.db.execute(stmt.order_by(FundingAccount.id.asc())).scalars().all()
        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        page_rows = rows[start:end]
        data = [
            {
                "id": row.id,
                "activity_id": row.activity_id,
                "account_code": row.account_code,
                "name": row.name,
            }
            for row in page_rows
        ]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return {"items": data, "page": page, "page_size": page_size, "total": total, "total_pages": total_pages}

    def create_transaction(
        self,
        *,
        activity_id: int,
        funding_account_id: int,
        tx_type: str,
        category: str,
        amount: float,
        occurred_at: str,
        note: str | None,
        invoice_upload_session_id: str | None,
        created_by: int,
        idempotency_key: str,
    ) -> dict:
        activity = (
            self.db.execute(
                select(Activity).where(Activity.id == activity_id).where(Activity.deleted_at.is_(None)).with_for_update().limit(1)
            )
            .scalar_one_or_none()
        )
        if activity is None:
            raise not_found("Activity not found")

        existing = (
            self.db.execute(
                select(FundingTransaction)
                .where(FundingTransaction.activity_id == activity_id)
                .where(FundingTransaction.idempotency_key == idempotency_key)
                .where(FundingTransaction.deleted_at.is_(None))
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if existing is not None:
            return self._tx_payload(existing, activity)

        account = (
            self.db.execute(
                select(FundingAccount)
                .where(FundingAccount.id == funding_account_id)
                .where(FundingAccount.deleted_at.is_(None))
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if account is None:
            raise not_found("Funding account not found")
        if account.activity_id != activity_id:
            raise validation_error("Funding account does not belong to activity")

        invoice_blob_id = None
        if invoice_upload_session_id:
            session = (
                self.db.execute(
                    select(UploadSession)
                    .where(UploadSession.session_id == invoice_upload_session_id)
                    .where(UploadSession.created_by == created_by)
                    .where(UploadSession.status == "FINALIZED")
                    .limit(1)
                )
                .scalar_one_or_none()
            )
            if session is None:
                raise not_found("Invoice upload session not found or not finalized")
            blob = self._latest_blob_for_upload_session(session)
            if blob is None:
                raise not_found("Invoice file blob not found")
            invoice_blob_id = blob.id

        occurred_dt = self._parse_iso_datetime(occurred_at)

        tx_status = "CONFIRMED"
        budget_warning = {
            "triggered": False,
            "threshold": 1.10,
            "current_ratio": 0,
            "requires_secondary_confirmation": False,
        }

        if tx_type == "EXPENSE":
            current_confirmed_expense = (
                self.db.execute(
                    select(func.coalesce(func.sum(FundingTransaction.amount), 0))
                    .where(FundingTransaction.activity_id == activity_id)
                    .where(FundingTransaction.tx_type == "EXPENSE")
                    .where(FundingTransaction.tx_status == "CONFIRMED")
                    .where(FundingTransaction.deleted_at.is_(None))
                )
                .scalar_one()
            )
            projected = float(current_confirmed_expense) + float(amount)
            ratio = (projected / float(activity.budget_total)) if float(activity.budget_total) > 0 else 999999.0
            if ratio > 1.10:
                tx_status = "PENDING_CONFIRMATION"
                budget_warning = {
                    "triggered": True,
                    "threshold": 1.10,
                    "current_ratio": round(ratio, 4),
                    "requires_secondary_confirmation": True,
                }

        tx = FundingTransaction(
            activity_id=activity_id,
            funding_account_id=funding_account_id,
            tx_status=tx_status,
            tx_type=tx_type,
            category=category,
            amount=amount,
            occurred_at=occurred_dt,
            note=note,
            invoice_file_blob_id=invoice_blob_id,
            created_by=created_by,
            idempotency_key=idempotency_key,
        )
        self.db.add(tx)
        self.db.add(
            AuditLog(
                actor_user_id=created_by,
                actor_username=None,
                actor_role_code=None,
                action="CREATE_FUNDING_TRANSACTION",
                entity_type="FUNDING_TRANSACTION",
                entity_id=idempotency_key,
                request_id=None,
                ip_address=None,
                result="SUCCESS",
                error_code=None,
                before_snapshot=None,
                after_snapshot={
                    "activity_id": activity_id,
                    "funding_account_id": funding_account_id,
                    "tx_type": tx_type,
                    "tx_status": tx_status,
                    "amount": float(amount),
                },
            )
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise conflict("CONFLICT", "Transaction conflict detected") from exc

        self.db.refresh(tx)
        payload = self._tx_payload(tx, activity)
        payload["budget_warning"] = budget_warning
        return payload

    def confirm_overrun(self, *, transaction_id: int, actor_user_id: int) -> dict:
        tx = (
            self.db.execute(
                select(FundingTransaction)
                .where(FundingTransaction.id == transaction_id)
                .where(FundingTransaction.deleted_at.is_(None))
                .with_for_update()
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if tx is None:
            raise not_found("Transaction not found")
        if tx.tx_status != "PENDING_CONFIRMATION":
            raise conflict("INVALID_TRANSACTION_STATUS", "Transaction is not pending confirmation")

        tx.tx_status = "CONFIRMED"
        tx.updated_at = datetime.utcnow()
        self.db.add(tx)
        self.db.add(
            AuditLog(
                actor_user_id=actor_user_id,
                actor_username=None,
                actor_role_code=None,
                action="CONFIRM_OVERRUN",
                entity_type="FUNDING_TRANSACTION",
                entity_id=str(tx.id),
                request_id=None,
                ip_address=None,
                result="SUCCESS",
                error_code=None,
                before_snapshot={"tx_status": "PENDING_CONFIRMATION"},
                after_snapshot={"tx_status": "CONFIRMED"},
            )
        )
        self.db.commit()
        self.db.refresh(tx)
        return {
            "transaction_id": tx.id,
            "tx_status": tx.tx_status,
            "confirmed_by": actor_user_id,
        }

    def list_transactions(
        self,
        *,
        activity_id: int,
        tx_type: str | None,
        category: str | None,
        from_dt: str | None,
        to_dt: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        stmt = (
            select(FundingTransaction)
            .where(FundingTransaction.activity_id == activity_id)
            .where(FundingTransaction.deleted_at.is_(None))
        )
        if tx_type:
            stmt = stmt.where(FundingTransaction.tx_type == tx_type)
        if category:
            stmt = stmt.where(FundingTransaction.category == category)
        if from_dt:
            stmt = stmt.where(FundingTransaction.occurred_at >= self._parse_iso_datetime(from_dt))
        if to_dt:
            stmt = stmt.where(FundingTransaction.occurred_at <= self._parse_iso_datetime(to_dt))

        rows = self.db.execute(stmt.order_by(FundingTransaction.occurred_at.desc())).scalars().all()
        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        page_rows = rows[start:end]

        data = [
            {
                "transaction_id": row.id,
                "activity_id": row.activity_id,
                "funding_account_id": row.funding_account_id,
                "tx_status": row.tx_status,
                "tx_type": row.tx_type,
                "category": row.category,
                "amount": float(row.amount),
                "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
                "note": row.note,
                "invoice_file_blob_id": row.invoice_file_blob_id,
            }
            for row in page_rows
        ]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return {"items": data, "page": page, "page_size": page_size, "total": total, "total_pages": total_pages}

    def statistics(self, *, activity_id: int, group_by: str, from_dt: str | None, to_dt: str | None) -> dict:
        if group_by not in {"category", "day", "week", "month"}:
            raise validation_error("group_by must be one of: category, day, week, month")

        stmt = (
            select(FundingTransaction)
            .where(FundingTransaction.activity_id == activity_id)
            .where(FundingTransaction.deleted_at.is_(None))
            .where(FundingTransaction.tx_status == "CONFIRMED")
        )
        if from_dt:
            stmt = stmt.where(FundingTransaction.occurred_at >= self._parse_iso_datetime(from_dt))
        if to_dt:
            stmt = stmt.where(FundingTransaction.occurred_at <= self._parse_iso_datetime(to_dt))

        rows = self.db.execute(stmt).scalars().all()

        buckets: dict[str, dict] = {}
        for row in rows:
            key = self._bucket_key(row.occurred_at, row.category, group_by)
            item = buckets.setdefault(
                key,
                {
                    "key": key,
                    "income_total": 0.0,
                    "expense_total": 0.0,
                    "net_total": 0.0,
                    "count": 0,
                },
            )
            amount = float(row.amount)
            if row.tx_type == "INCOME":
                item["income_total"] += amount
                item["net_total"] += amount
            else:
                item["expense_total"] += amount
                item["net_total"] -= amount
            item["count"] += 1

        data = list(buckets.values())
        data.sort(key=lambda x: x["key"])
        return {"activity_id": activity_id, "group_by": group_by, "items": data}

    def _latest_blob_for_upload_session(self, session: UploadSession) -> FileBlob | None:
        filename = session.original_filename
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else None

        stmt = select(FileBlob).where(FileBlob.original_filename == filename)
        if ext:
            stmt = stmt.where(FileBlob.storage_path.ilike(f"%.{ext}"))
        return self.db.execute(stmt.order_by(FileBlob.created_at.desc()).limit(1)).scalar_one_or_none()

    def _parse_iso_datetime(self, value: str) -> datetime:
        try:
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        except Exception as exc:  # noqa: BLE001
            raise validation_error("Invalid datetime format; expected ISO-8601") from exc

    def _bucket_key(self, occurred_at: datetime, category: str, group_by: str) -> str:
        if group_by == "category":
            return category
        if group_by == "day":
            return occurred_at.strftime("%Y-%m-%d")
        if group_by == "week":
            iso_year, iso_week, _ = occurred_at.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        return occurred_at.strftime("%Y-%m")

    def _tx_payload(self, tx: FundingTransaction, activity: Activity) -> dict:
        confirmed_expense = (
            self.db.execute(
                select(func.coalesce(func.sum(FundingTransaction.amount), 0))
                .where(FundingTransaction.activity_id == tx.activity_id)
                .where(FundingTransaction.tx_type == "EXPENSE")
                .where(FundingTransaction.tx_status == "CONFIRMED")
                .where(FundingTransaction.deleted_at.is_(None))
            )
            .scalar_one()
        )
        ratio = (float(confirmed_expense) / float(activity.budget_total)) if float(activity.budget_total) > 0 else 999999.0
        return {
            "transaction_id": tx.id,
            "tx_status": tx.tx_status,
            "activity_id": tx.activity_id,
            "funding_account_id": tx.funding_account_id,
            "tx_type": tx.tx_type,
            "category": tx.category,
            "amount": float(tx.amount),
            "occurred_at": tx.occurred_at.isoformat() if tx.occurred_at else None,
            "note": tx.note,
            "invoice_file_blob_id": tx.invoice_file_blob_id,
            "budget_warning": {
                "triggered": ratio > 1.10,
                "threshold": 1.10,
                "current_ratio": round(ratio, 4),
                "requires_secondary_confirmation": tx.tx_status == "PENDING_CONFIRMATION",
            },
        }
