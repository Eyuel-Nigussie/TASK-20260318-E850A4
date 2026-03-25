import csv
import json
import os
import shutil
import tarfile
import uuid
import hashlib
from cryptography.fernet import Fernet
import base64
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import conflict, not_found, validation_error
from app.models.audit_log import AuditLog
from app.models.backup_record import BackupRecord
from app.models.funding_transaction import FundingTransaction
from app.models.review_workflow_record import ReviewWorkflowRecord
from app.models.user import User


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


class SystemService:
    def __init__(self, db: Session):
        self.db = db

    def list_audit_logs(self, *, page: int, page_size: int) -> dict:
        total = int(self.db.execute(select(func.count(AuditLog.id))).scalar_one())
        start = (page - 1) * page_size
        page_rows = (
            self.db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).offset(start).limit(page_size)).scalars().all()
        )
        data = [
            {
                "id": row.id,
                "actor_user_id": row.actor_user_id,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "result": row.result,
                "error_code": row.error_code,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in page_rows
        ]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return {"items": data, "page": page, "page_size": page_size, "total": total, "total_pages": total_pages}

    def update_profile(self, *, user_id: int, id_number: str | None, contact: str | None) -> dict:
        user = self.db.execute(select(User).where(User.id == user_id).where(User.deleted_at.is_(None)).limit(1)).scalar_one_or_none()
        if user is None:
            raise not_found("User not found")
        if id_number is not None:
            user.id_number = id_number
        if contact is not None:
            user.contact = contact
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return {"user_id": user.id, "id_number": user.id_number, "contact": user.contact}

    def profile(self, *, requester_role: str, user_id: int) -> dict:
        user = self.db.execute(select(User).where(User.id == user_id).where(User.deleted_at.is_(None)).limit(1)).scalar_one_or_none()
        if user is None:
            raise not_found("User not found")

        id_number = user.id_number
        contact = user.contact
        if requester_role != "SYSTEM_ADMIN":
            id_number = self._mask(id_number)
            contact = self._mask(contact)

        return {
            "id": user.id,
            "username": user.username,
            "id_number": id_number,
            "contact": contact,
        }

    def run_backup(self, *, created_by: int) -> dict:
        _ensure_dir(settings.backup_root)
        _ensure_dir(settings.storage_root)

        now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_id = f"bkp_{now}_{uuid.uuid4().hex[:6]}"
        backup_dir = os.path.join(settings.backup_root, backup_id)
        _ensure_dir(backup_dir)

        db_dump_path = os.path.join(backup_dir, "db_dump.json")
        storage_archive_path = os.path.join(backup_dir, "storage.tar.gz")
        metadata_path = os.path.join(backup_dir, "metadata.json")

        snapshot = {
            "users": self._dump_rows(select(User)),
            "review_workflow_records": self._dump_rows(select(ReviewWorkflowRecord)),
            "funding_transactions": self._dump_rows(select(FundingTransaction)),
            "audit_logs": self._dump_rows(select(AuditLog)),
        }
        with open(db_dump_path, "w", encoding="utf-8") as fp:
            json.dump(snapshot, fp, default=str, indent=2)

        with tarfile.open(storage_archive_path, "w:gz") as tar:
            tar.add(settings.storage_root, arcname="storage")

        metadata = {
            "backup_id": backup_id,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": created_by,
            "db_dump_path": db_dump_path,
            "storage_archive_path": storage_archive_path,
        }
        with open(metadata_path, "w", encoding="utf-8") as fp:
            json.dump(metadata, fp, indent=2)

        row = BackupRecord(
            backup_id=backup_id,
            db_dump_path=db_dump_path,
            storage_archive_path=storage_archive_path,
            metadata_path=metadata_path,
            status="READY",
            created_by=created_by,
        )
        self.db.add(row)
        self.db.add(
            AuditLog(
                actor_user_id=created_by,
                actor_username=None,
                actor_role_code=None,
                action="BACKUP_RUN",
                entity_type="BACKUP",
                entity_id=backup_id,
                request_id=None,
                ip_address=None,
                result="SUCCESS",
                error_code=None,
                before_snapshot=None,
                after_snapshot={
                    "db_dump_path": db_dump_path,
                    "storage_archive_path": storage_archive_path,
                    "metadata_path": metadata_path,
                },
            )
        )
        self.db.commit()
        self.db.refresh(row)
        return {"backup_id": row.backup_id, "status": row.status, "metadata_path": row.metadata_path}

    def backup_history(self, *, page: int, page_size: int) -> dict:
        total = int(self.db.execute(select(func.count(BackupRecord.id))).scalar_one())
        start = (page - 1) * page_size
        page_rows = (
            self.db.execute(select(BackupRecord).order_by(BackupRecord.created_at.desc()).offset(start).limit(page_size)).scalars().all()
        )
        data = [
            {
                "backup_id": row.backup_id,
                "status": row.status,
                "created_by": row.created_by,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in page_rows
        ]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return {"items": data, "page": page, "page_size": page_size, "total": total, "total_pages": total_pages}

    def restore_backup(self, *, backup_id: str, confirm: bool, pre_restore_backup: bool, requester_id: int) -> dict:
        if not confirm:
            raise validation_error("Restore requires explicit confirmation")

        record = (
            self.db.execute(select(BackupRecord).where(BackupRecord.backup_id == backup_id).limit(1)).scalar_one_or_none()
        )
        if record is None:
            raise not_found("Backup not found")
        if record.status != "READY":
            raise conflict("BACKUP_NOT_READY", "Backup record is not ready for restore")

        pre_backup_id = None
        if pre_restore_backup:
            pre_result = self.run_backup(created_by=requester_id)
            pre_backup_id = pre_result["backup_id"]

        restore_staging = os.path.join(settings.backup_root, f"restore_{backup_id}")
        if os.path.exists(restore_staging):
            shutil.rmtree(restore_staging)
        _ensure_dir(restore_staging)

        with tarfile.open(record.storage_archive_path, "r:gz") as tar:
            tar.extractall(path=restore_staging)

        restored_storage = os.path.join(restore_staging, "storage")
        if not os.path.isdir(restored_storage):
            raise conflict("RESTORE_FAILED", "Backup storage archive is invalid")

        try:
            self._replace_directory_contents(settings.storage_root, restored_storage)
        except OSError as exc:
            raise conflict("RESTORE_FAILED", f"Failed to restore storage in-place: {exc}") from exc

        return {
            "backup_id": backup_id,
            "restored": True,
            "pre_restore_backup_id": pre_backup_id,
            "mode": "in_place",
        }

    def export_csv(self, *, export_type: str, actor_id: int) -> dict:
        if export_type not in {"reconciliation", "audit", "compliance", "whitelist-policy"}:
            raise validation_error("Unsupported export type")

        _ensure_dir(settings.export_root)
        filename = f"{export_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        output_path = os.path.join(settings.export_root, filename)

        if export_type == "reconciliation":
            headers = ["transaction_id", "activity_id", "tx_type", "tx_status", "amount", "occurred_at"]
            rows = self.db.execute(select(FundingTransaction)).scalars().all()
            values = [[row.id, row.activity_id, row.tx_type, row.tx_status, float(row.amount), row.occurred_at] for row in rows]
        elif export_type == "audit":
            headers = ["audit_id", "actor_user_id", "action", "entity_type", "entity_id", "result", "created_at"]
            rows = self.db.execute(select(AuditLog)).scalars().all()
            values = [[row.id, row.actor_user_id, row.action, row.entity_type, row.entity_id, row.result, row.created_at] for row in rows]
        elif export_type == "compliance":
            headers = ["registration_id", "status", "row_version", "updated_at"]
            rows = self.db.execute(select(ReviewWorkflowRecord)).scalars().all()
            values = [[row.registration_form_id, row.to_state, row.id, row.created_at] for row in rows]
        else:
            headers = ["policy_scope", "note"]
            values = [["activity", "local whitelist policy export"]]

        with open(output_path, "w", newline="", encoding="utf-8") as fp:
            writer = csv.writer(fp)
            writer.writerow(headers)
            writer.writerows(values)

        self.db.add(
            AuditLog(
                actor_user_id=actor_id,
                actor_username=None,
                actor_role_code=None,
                action="EXPORT",
                entity_type="EXPORT",
                entity_id=filename,
                request_id=None,
                ip_address=None,
                result="SUCCESS",
                error_code=None,
                before_snapshot=None,
                after_snapshot={"type": export_type, "path": output_path},
            )
        )
        self.db.commit()

        return {"type": export_type, "path": output_path}

    def _mask(self, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) <= 4:
            return "*" * len(value)
        return "****" + value[-4:]

    def _dump_rows(self, stmt) -> list[dict]:
        rows = self.db.execute(stmt).scalars().all()
        output = []
        for row in rows:
            payload = {}
            for column in row.__table__.columns:
                value = getattr(row, column.name)
                if isinstance(value, datetime):
                    payload[column.name] = value.isoformat()
                else:
                    payload[column.name] = value
            output.append(payload)
        return output

    def _replace_directory_contents(self, target_dir: str, source_dir: str) -> None:
        _ensure_dir(target_dir)

        for name in os.listdir(target_dir):
            path = os.path.join(target_dir, name)
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

        for name in os.listdir(source_dir):
            src = os.path.join(source_dir, name)
            dst = os.path.join(target_dir, name)
            if os.path.isdir(src) and not os.path.islink(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

    def encrypt_sensitive_config_value(self, value: str) -> str:
        key = self._derive_local_fernet_key()
        token = Fernet(key).encrypt(value.encode("utf-8"))
        return token.decode("ascii")

    def _derive_local_fernet_key(self) -> bytes:
        seed = os.getenv("JWT_ACCESS_SECRET", "local-dev-key").encode("utf-8")
        digest = hashlib.sha256(seed).digest()
        return base64.urlsafe_b64encode(digest)
