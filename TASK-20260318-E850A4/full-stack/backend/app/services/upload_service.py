import hashlib
import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import conflict, not_found, payload_too_large, validation_error
from app.models.activity import Activity
from app.models.file_blob import FileBlob
from app.models.material_checklist import MaterialChecklist
from app.models.material_item import MaterialItem
from app.models.material_version import MaterialVersion
from app.models.registration_form import RegistrationForm
from app.models.upload_session import UploadSession


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_content_range(value: str) -> tuple[int, int, int]:
    # format: bytes start-end/total
    try:
        unit, rest = value.split(" ", 1)
        range_part, total_part = rest.split("/", 1)
        start_str, end_str = range_part.split("-", 1)
        if unit.strip().lower() != "bytes":
            raise ValueError("invalid unit")
        start = int(start_str)
        end = int(end_str)
        total = int(total_part)
        return start, end, total
    except Exception as exc:  # noqa: BLE001
        raise validation_error("Invalid Content-Range header") from exc


class UploadService:
    def __init__(self, db: Session):
        self.db = db

    def _get_registration_and_checklist(self, registration_id: int, checklist_id: int, actor_user_id: int):
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

        if registration.applicant_user_id != actor_user_id:
            raise validation_error("Registration does not belong to current applicant")

        checklist = (
            self.db.execute(
                select(MaterialChecklist)
                .where(MaterialChecklist.id == checklist_id)
                .where(MaterialChecklist.activity_id == registration.activity_id)
                .where(MaterialChecklist.deleted_at.is_(None))
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if checklist is None:
            raise not_found("Checklist item not found")

        activity = (
            self.db.execute(
                select(Activity)
                .where(Activity.id == registration.activity_id)
                .where(Activity.deleted_at.is_(None))
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if activity is None:
            raise not_found("Activity not found")

        now = _utc_now()
        if now > activity.registration_deadline:
            if registration.status != "SUPPLEMENTED" or activity.supplement_deadline is None or now > activity.supplement_deadline:
                raise conflict("MATERIALS_LOCKED", "Materials are locked after deadline")

        return registration, checklist, activity

    def init_upload(
        self,
        *,
        registration_id: int,
        checklist_id: int,
        filename: str,
        mime_type: str,
        size_bytes: int,
        actor_user_id: int,
    ) -> dict:
        registration, checklist, _ = self._get_registration_and_checklist(registration_id, checklist_id, actor_user_id)

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        allowed = {item.lower() for item in checklist.allowed_extensions}
        if ext not in allowed:
            raise validation_error("File extension is not allowed", {"allowed_extensions": sorted(allowed)})

        if size_bytes > 20971520 or size_bytes > checklist.max_file_size_bytes:
            raise payload_too_large("File exceeds per-file size limit (20MB)")

        if registration.total_material_size_bytes + size_bytes > 209715200:
            raise payload_too_large("Total upload size exceeds 200MB for this application")

        session_id = f"upl_{uuid.uuid4().hex}"
        tmp_dir = os.path.join(settings.storage_root, ".tmp", session_id)
        os.makedirs(tmp_dir, exist_ok=True)
        temp_path = os.path.join(tmp_dir, "upload.bin")
        with open(temp_path, "wb"):
            pass

        expires_at = _utc_now() + timedelta(minutes=settings.upload_session_ttl_minutes)
        item = UploadSession(
            session_id=session_id,
            registration_form_id=registration_id,
            checklist_id=checklist_id,
            original_filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            received_bytes=0,
            status="INITIATED",
            temp_file_path=temp_path,
            uploaded_chunks=[],
            created_by=actor_user_id,
            expires_at=expires_at,
        )
        self.db.add(item)
        self.db.commit()

        return {
            "upload_session_id": session_id,
            "max_chunk_size": settings.upload_chunk_max_bytes,
            "expires_at": expires_at.isoformat(),
        }

    def upload_chunk(self, *, session_id: str, chunk_index: int, content_range: str, content: bytes, actor_user_id: int) -> dict:
        session = (
            self.db.execute(
                select(UploadSession)
                .where(UploadSession.session_id == session_id)
                .where(UploadSession.created_by == actor_user_id)
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if session is None:
            raise not_found("Upload session not found")

        if _utc_now() > session.expires_at:
            session.status = "FAILED"
            self.db.add(session)
            self.db.commit()
            raise conflict("UPLOAD_SESSION_EXPIRED", "Upload session expired")

        if len(content) > settings.upload_chunk_max_bytes:
            raise payload_too_large("Chunk exceeds maximum chunk size")

        start, end, total = _parse_content_range(content_range)
        if total != session.size_bytes:
            raise validation_error("Content-Range total does not match upload size")

        if end - start + 1 != len(content):
            raise validation_error("Content-Range does not match chunk payload size")

        uploaded_chunks = set(session.uploaded_chunks or [])
        if chunk_index in uploaded_chunks:
            return {
                "upload_session_id": session.session_id,
                "received_bytes": session.received_bytes,
                "status": session.status,
                "chunk_already_uploaded": True,
            }

        if start != session.received_bytes:
            raise conflict(
                "INVALID_CHUNK_ORDER",
                "Chunk out of order",
                {"expected_start": session.received_bytes, "actual_start": start},
            )

        os.makedirs(os.path.dirname(session.temp_file_path), exist_ok=True)
        with open(session.temp_file_path, "ab") as fp:
            fp.write(content)

        session.received_bytes += len(content)
        uploaded_chunks.add(chunk_index)
        session.uploaded_chunks = sorted(uploaded_chunks)
        session.status = "UPLOADING"
        session.updated_at = datetime.utcnow()
        self.db.add(session)
        self.db.commit()

        return {
            "upload_session_id": session.session_id,
            "received_bytes": session.received_bytes,
            "status": session.status,
            "chunk_already_uploaded": False,
        }

    def finalize_upload(
        self,
        *,
        session_id: str,
        idempotency_key: str,
        registration_id: int,
        checklist_id: int,
        status_label: str,
        correction_reason: str | None,
        actor_user_id: int,
    ) -> dict:
        session = (
            self.db.execute(
                select(UploadSession)
                .where(UploadSession.session_id == session_id)
                .where(UploadSession.created_by == actor_user_id)
                .with_for_update()
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if session is None:
            raise not_found("Upload session not found")

        if session.registration_form_id != registration_id or session.checklist_id != checklist_id:
            raise validation_error("Upload session does not match finalize payload")

        if session.idempotency_key is not None:
            if session.idempotency_key != idempotency_key:
                raise conflict("IDEMPOTENCY_KEY_MISMATCH", "Finalize already executed with a different idempotency key")
            existing = self._find_latest_material_version(registration_id, checklist_id)
            if existing is None:
                raise conflict("UPLOAD_FINALIZE_STATE_INVALID", "Finalize already called but material version not found")
            return existing

        if not os.path.exists(session.temp_file_path):
            raise not_found("Upload temporary file not found")

        if session.received_bytes != session.size_bytes:
            raise conflict(
                "UPLOAD_INCOMPLETE",
                "Cannot finalize before all bytes are uploaded",
                {"received_bytes": session.received_bytes, "size_bytes": session.size_bytes},
            )

        registration, checklist, activity = self._get_registration_and_checklist(registration_id, checklist_id, actor_user_id)
        self.db.refresh(registration)

        if status_label == "NEEDS_CORRECTION" and not correction_reason:
            raise validation_error("Correction reason is required when status label is NEEDS_CORRECTION")

        sha256 = self._hash_file(session.temp_file_path)

        material_item = (
            self.db.execute(
                select(MaterialItem)
                .where(MaterialItem.registration_form_id == registration_id)
                .where(MaterialItem.checklist_id == checklist_id)
                .where(MaterialItem.deleted_at.is_(None))
                .with_for_update()
                .limit(1)
            )
            .scalar_one_or_none()
        )

        if material_item is None:
            material_item = MaterialItem(
                registration_form_id=registration_id,
                checklist_id=checklist_id,
                latest_label=status_label,
                version_count=0,
            )
            self.db.add(material_item)
            self.db.flush()

        latest_version = (
            self.db.execute(
                select(MaterialVersion)
                .where(MaterialVersion.material_item_id == material_item.id)
                .where(MaterialVersion.deleted_at.is_(None))
                .order_by(MaterialVersion.version_no.desc())
                .limit(1)
            )
            .scalar_one_or_none()
        )

        if latest_version is not None:
            prev_blob = self.db.execute(select(FileBlob).where(FileBlob.id == latest_version.file_blob_id).limit(1)).scalar_one_or_none()
            if prev_blob is not None and prev_blob.sha256 == sha256:
                raise conflict(
                    "DUPLICATE_MATERIAL_VERSION",
                    "Exact same file already uploaded for this checklist item",
                    {"sha256": sha256},
                )

        if material_item.version_count >= 3:
            raise conflict("MATERIAL_VERSION_LIMIT_REACHED", "Material version limit (3) reached")

        exact_version_count = (
            self.db.execute(
                select(MaterialVersion)
                .where(MaterialVersion.material_item_id == material_item.id)
                .where(MaterialVersion.deleted_at.is_(None))
                .order_by(MaterialVersion.version_no.desc())
            )
            .scalars()
            .all()
        )
        if len(exact_version_count) >= 3:
            raise conflict("MATERIAL_VERSION_LIMIT_REACHED", "Material version limit (3) reached")

        blob = self.db.execute(select(FileBlob).where(FileBlob.sha256 == sha256).limit(1)).scalar_one_or_none()
        ext = session.original_filename.rsplit(".", 1)[-1].lower() if "." in session.original_filename else "bin"

        if blob is None:
            final_dir = os.path.join(
                settings.storage_root,
                "activities",
                str(activity.id),
                "registrations",
                str(registration.id),
                "materials",
                str(material_item.id),
            )
            os.makedirs(final_dir, exist_ok=True)
            final_path = os.path.join(final_dir, f"v{material_item.version_count + 1}_{sha256}.{ext}")
            if not os.path.exists(final_path):
                shutil.move(session.temp_file_path, final_path)
            blob = FileBlob(
                sha256=sha256,
                storage_path=final_path,
                original_filename=session.original_filename,
                mime_type=session.mime_type,
                size_bytes=session.size_bytes,
            )
            self.db.add(blob)
            self.db.flush()
        else:
            if os.path.exists(session.temp_file_path):
                os.remove(session.temp_file_path)

        new_version_no = material_item.version_count + 1
        version = MaterialVersion(
            material_item_id=material_item.id,
            version_no=new_version_no,
            status_label=status_label,
            file_blob_id=blob.id,
            correction_reason=correction_reason,
            uploaded_by=actor_user_id,
        )
        self.db.add(version)

        material_item.version_count = new_version_no
        material_item.latest_label = status_label
        material_item.updated_at = datetime.utcnow()

        registration.total_material_size_bytes += session.size_bytes
        if registration.total_material_size_bytes > 209715200:
            raise payload_too_large("Total upload size exceeds 200MB for this application")

        session.idempotency_key = idempotency_key
        session.status = "FINALIZED"
        session.updated_at = datetime.utcnow()

        self.db.add(material_item)
        self.db.add(registration)
        self.db.add(session)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise conflict("CONFLICT", "Finalize failed due to concurrent update") from exc

        tmp_dir = os.path.dirname(session.temp_file_path)
        if os.path.isdir(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except OSError:
                pass

        return {
            "material_item_id": material_item.id,
            "new_version_no": new_version_no,
            "sha256": sha256,
            "size_bytes": session.size_bytes,
            "total_material_size_bytes": registration.total_material_size_bytes,
        }

    def _hash_file(self, path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as fp:
            while True:
                chunk = fp.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def _find_latest_material_version(self, registration_id: int, checklist_id: int) -> dict | None:
        item = (
            self.db.execute(
                select(MaterialItem)
                .where(MaterialItem.registration_form_id == registration_id)
                .where(MaterialItem.checklist_id == checklist_id)
                .where(MaterialItem.deleted_at.is_(None))
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if item is None:
            return None

        version = (
            self.db.execute(
                select(MaterialVersion)
                .where(MaterialVersion.material_item_id == item.id)
                .where(MaterialVersion.deleted_at.is_(None))
                .order_by(MaterialVersion.version_no.desc())
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if version is None:
            return None

        blob = self.db.execute(select(FileBlob).where(FileBlob.id == version.file_blob_id).limit(1)).scalar_one_or_none()
        if blob is None:
            return None

        registration = self.db.execute(select(RegistrationForm).where(RegistrationForm.id == registration_id).limit(1)).scalar_one_or_none()
        if registration is None:
            return None

        return {
            "material_item_id": item.id,
            "new_version_no": version.version_no,
            "sha256": blob.sha256,
            "size_bytes": blob.size_bytes,
            "total_material_size_bytes": registration.total_material_size_bytes,
        }

    def list_materials(self, *, registration_id: int, actor_user_id: int) -> dict:
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
        if registration.applicant_user_id != actor_user_id:
            raise validation_error("Registration does not belong to current applicant")

        rows = (
            self.db.execute(
                select(MaterialItem, MaterialChecklist)
                .join(MaterialChecklist, MaterialChecklist.id == MaterialItem.checklist_id)
                .where(MaterialItem.registration_form_id == registration_id)
                .where(MaterialItem.deleted_at.is_(None))
                .where(MaterialChecklist.deleted_at.is_(None))
                .order_by(MaterialItem.id.asc())
            )
            .all()
        )

        data = []
        for material_item, checklist in rows:
            data.append(
                {
                    "material_item_id": material_item.id,
                    "checklist_id": checklist.id,
                    "checklist_key": checklist.key,
                    "checklist_label": checklist.label,
                    "latest_label": material_item.latest_label,
                    "version_count": material_item.version_count,
                }
            )

        return {
            "registration_id": registration_id,
            "total_material_size_bytes": registration.total_material_size_bytes,
            "items": data,
        }

    def material_history(self, *, registration_id: int, material_item_id: int, actor_user_id: int) -> dict:
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
        if registration.applicant_user_id != actor_user_id:
            raise validation_error("Registration does not belong to current applicant")

        material_item = (
            self.db.execute(
                select(MaterialItem)
                .where(MaterialItem.id == material_item_id)
                .where(MaterialItem.registration_form_id == registration_id)
                .where(MaterialItem.deleted_at.is_(None))
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if material_item is None:
            raise not_found("Material item not found")

        versions = (
            self.db.execute(
                select(MaterialVersion, FileBlob)
                .join(FileBlob, FileBlob.id == MaterialVersion.file_blob_id)
                .where(MaterialVersion.material_item_id == material_item.id)
                .where(MaterialVersion.deleted_at.is_(None))
                .order_by(MaterialVersion.version_no.desc())
            )
            .all()
        )

        data = []
        for version, blob in versions:
            data.append(
                {
                    "version_no": version.version_no,
                    "status_label": version.status_label,
                    "correction_reason": version.correction_reason,
                    "sha256": blob.sha256,
                    "size_bytes": blob.size_bytes,
                    "original_filename": blob.original_filename,
                    "uploaded_at": version.uploaded_at.isoformat() if version.uploaded_at else None,
                }
            )

        return {
            "registration_id": registration_id,
            "material_item_id": material_item_id,
            "version_count": material_item.version_count,
            "history": data,
        }
