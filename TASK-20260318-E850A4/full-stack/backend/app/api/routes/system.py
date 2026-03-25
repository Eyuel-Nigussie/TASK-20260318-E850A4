from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_request_id
from app.core.database import get_db
from app.core.errors import forbidden
from app.schemas.common import MetaInfo
from app.schemas.system import BackupRestoreRequest, ProfileUpdateRequest
from app.security.authz import get_current_user
from app.services.system_service import SystemService

router = APIRouter(tags=["system"])


def _ensure_admin(principal: dict) -> None:
    role_code = principal["role"].code
    if role_code != "SYSTEM_ADMIN":
        raise forbidden("System admin permission required")


@router.get("/audit/logs")
def audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_admin(principal)
    service = SystemService(db)
    data = service.list_audit_logs(page=page, page_size=page_size)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.get("/users/{user_id}/profile")
def user_profile(
    user_id: int,
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    service = SystemService(db)
    data = service.profile(requester_role=principal["role"].code, user_id=user_id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.put("/users/{user_id}/profile")
def update_user_profile(
    user_id: int,
    payload: ProfileUpdateRequest,
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_admin(principal)
    service = SystemService(db)
    data = service.update_profile(user_id=user_id, id_number=payload.id_number, contact=payload.contact)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/system/backup/run")
def run_backup(
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_admin(principal)
    service = SystemService(db)
    data = service.run_backup(created_by=principal["user"].id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.get("/system/backup/history")
def backup_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_admin(principal)
    service = SystemService(db)
    data = service.backup_history(page=page, page_size=page_size)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/system/backup/restore")
def restore_backup(
    payload: BackupRestoreRequest,
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_admin(principal)
    service = SystemService(db)
    data = service.restore_backup(
        backup_id=payload.backup_id,
        confirm=payload.confirm,
        pre_restore_backup=payload.pre_restore_backup,
        requester_id=principal["user"].id,
    )
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/exports/reconciliation")
def export_reconciliation(
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_admin(principal)
    service = SystemService(db)
    data = service.export_csv(export_type="reconciliation", actor_id=principal["user"].id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/exports/audit")
def export_audit(
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_admin(principal)
    service = SystemService(db)
    data = service.export_csv(export_type="audit", actor_id=principal["user"].id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/exports/compliance")
def export_compliance(
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_admin(principal)
    service = SystemService(db)
    data = service.export_csv(export_type="compliance", actor_id=principal["user"].id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/exports/whitelist-policy")
def export_whitelist(
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_admin(principal)
    service = SystemService(db)
    data = service.export_csv(export_type="whitelist-policy", actor_id=principal["user"].id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}
