import uuid
from datetime import datetime, timedelta, timezone
import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.errors import ApiError
from app.models import Role, User
from app.models.activity import Activity
from app.models.funding_account import FundingAccount
from app.models.material_checklist import MaterialChecklist
from app.models.registration_form import RegistrationForm
from app.security.passwords import generate_salt, hash_password
from app.services.system_service import SystemService

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in settings.cors_origins.split(",") if item.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

logger = logging.getLogger(__name__)


async def backup_scheduler_loop() -> None:
    if not settings.backup_schedule_enabled:
        return
    while True:
        now = datetime.now(timezone.utc)
        next_run = now.replace(hour=settings.backup_schedule_hour_utc, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run = next_run + timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        db = SessionLocal()
        try:
            SystemService(db).run_backup(created_by=1)
        except Exception as exc:
            from app.models.audit_log import AuditLog
            try:
                db.add(
                    AuditLog(
                        actor_user_id=1,
                        actor_username="scheduler",
                        actor_role_code="SYSTEM",
                        action="BACKUP_RUN",
                        entity_type="BACKUP",
                        entity_id="daily-schedule",
                        request_id=None,
                        ip_address=None,
                        result="FAILED",
                        error_code="SCHEDULER_ERROR",
                        before_snapshot=None,
                        after_snapshot={"error": str(exc)},
                    )
                )
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("Failed to persist scheduler backup failure audit log")
        finally:
            db.close()


def seed_initial_data() -> None:
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS id_number VARCHAR(64)"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS contact VARCHAR(64)"))
        conn.execute(text("ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS finalized_file_blob_id BIGINT REFERENCES file_blobs(id)"))
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS backup_records (
                    id BIGSERIAL PRIMARY KEY,
                    backup_id VARCHAR(64) NOT NULL UNIQUE,
                    db_dump_path TEXT NOT NULL,
                    storage_archive_path TEXT NOT NULL,
                    metadata_path TEXT NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    created_by BIGINT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS quality_validation_results (
                    id BIGSERIAL PRIMARY KEY,
                    activity_id BIGINT NOT NULL REFERENCES activities(id),
                    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    approval_rate NUMERIC(6,3) NOT NULL,
                    correction_rate NUMERIC(6,3) NOT NULL,
                    overspending_rate NUMERIC(6,3) NOT NULL,
                    metrics_payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS data_collection_batches (
                    id BIGSERIAL PRIMARY KEY,
                    activity_id BIGINT NOT NULL REFERENCES activities(id),
                    batch_code VARCHAR(64) NOT NULL,
                    source_scope JSONB NOT NULL,
                    whitelist_policy JSONB NOT NULL,
                    created_by BIGINT NOT NULL REFERENCES users(id),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    deleted_at TIMESTAMPTZ,
                    UNIQUE(activity_id, batch_code)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'ck_reg_total_material_size'
                    ) THEN
                        ALTER TABLE registration_forms
                        ADD CONSTRAINT ck_reg_total_material_size
                        CHECK (total_material_size_bytes >= 0 AND total_material_size_bytes <= 209715200);
                    END IF;
                END $$;
                """
            )
        )

    db = SessionLocal()
    try:
        existing_roles = {item.code for item in db.query(Role).all()}
        for code, name in [
            ("APPLICANT", "Applicant"),
            ("REVIEWER", "Reviewer"),
            ("FINANCIAL_ADMIN", "Financial Administrator"),
            ("SYSTEM_ADMIN", "System Administrator"),
        ]:
            if code not in existing_roles:
                db.add(Role(code=code, name=name))
        db.commit()

        admin = db.query(User).filter(User.username == "sysadmin", User.deleted_at.is_(None)).first()
        if admin is None:
            role = db.query(Role).filter(Role.code == "SYSTEM_ADMIN").first()
            if role is not None:
                salt = generate_salt()
                password_hash = hash_password("Admin#123456", salt)
                db.add(
                    User(
                        username="sysadmin",
                        password_hash=password_hash,
                        password_salt=salt,
                        role_id=role.id,
                        is_active=True,
                    )
                )
                db.commit()

        admin = db.query(User).filter(User.username == "sysadmin", User.deleted_at.is_(None)).first()
        if admin is not None:
            activity = db.query(Activity).filter(Activity.code == "ACT-001", Activity.deleted_at.is_(None)).first()
            if activity is None:
                now = datetime.now(timezone.utc)
                activity = Activity(
                    code="ACT-001",
                    title="Seed Activity",
                    registration_deadline=now + timedelta(days=365),
                    supplement_deadline=now + timedelta(days=365),
                    budget_total=100000,
                    currency="USD",
                    created_by=admin.id,
                )
                db.add(activity)
                db.commit()
                db.refresh(activity)

            checklist = db.query(MaterialChecklist).filter(
                MaterialChecklist.activity_id == activity.id,
                MaterialChecklist.key == "id_document",
                MaterialChecklist.deleted_at.is_(None),
            ).first()
            if checklist is None:
                db.add(
                    MaterialChecklist(
                        activity_id=activity.id,
                        key="id_document",
                        label="ID Document",
                        is_required=True,
                        allowed_extensions=["pdf", "jpg", "png"],
                        max_file_size_bytes=20971520,
                    )
                )
                db.commit()

            registration = db.query(RegistrationForm).filter(
                RegistrationForm.activity_id == activity.id,
                RegistrationForm.applicant_user_id == admin.id,
                RegistrationForm.deleted_at.is_(None),
            ).first()
            if registration is None:
                db.add(
                    RegistrationForm(
                        activity_id=activity.id,
                        applicant_user_id=admin.id,
                        form_payload={"seed": True},
                        status="DRAFT",
                    )
                )
                db.commit()

            account = db.query(FundingAccount).filter(
                FundingAccount.activity_id == activity.id,
                FundingAccount.account_code == "MAIN",
                FundingAccount.deleted_at.is_(None),
            ).first()
            if account is None:
                db.add(
                    FundingAccount(
                        activity_id=activity.id,
                        account_code="MAIN",
                        name="Main Activity Account",
                    )
                )
                db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup_event() -> None:
    seed_initial_data()
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(backup_scheduler_loop())
    except RuntimeError:
        pass


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    request_id = request.headers.get("x-request-id") if request.headers else None
    if not request_id:
        request_id = f"req_{uuid.uuid4().hex}"
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "INTERNAL_ERROR", "message": str(exc.detail), "details": {}}
    payload = {
        "success": False,
        "error": {
            "code": detail.get("code", "INTERNAL_ERROR"),
            "message": detail.get("message", "Unhandled error"),
            "details": detail.get("details", {}),
            "request_id": request_id,
        },
    }
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("x-request-id") if request.headers else None
    if not request_id:
        request_id = f"req_{uuid.uuid4().hex}"
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": {"errors": exc.errors()},
                "request_id": request_id,
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("x-request-id") if request.headers else None
    if not request_id:
        request_id = f"req_{uuid.uuid4().hex}"
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "details": {"error": str(exc)},
                "request_id": request_id,
            },
        },
    )
