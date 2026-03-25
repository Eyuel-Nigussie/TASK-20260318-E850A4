from fastapi import APIRouter, Depends, Header, Path, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_request_id
from app.core.database import get_db
from app.core.errors import validation_error
from app.schemas.common import MetaInfo
from app.schemas.upload import UploadFinalizeRequest, UploadInitRequest
from app.security.authz import get_current_user
from app.services.upload_service import UploadService

router = APIRouter(tags=["uploads"])


@router.post("/registrations/{registration_id}/materials/{checklist_id}/upload-init")
def upload_init(
    payload: UploadInitRequest,
    registration_id: int = Path(gt=0),
    checklist_id: int = Path(gt=0),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    service = UploadService(db)
    data = service.init_upload(
        registration_id=registration_id,
        checklist_id=checklist_id,
        filename=payload.filename,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        actor_user_id=principal["user"].id,
    )
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.put("/uploads/{upload_session_id}/chunk/{chunk_index}")
async def upload_chunk(
    request: Request,
    upload_file: UploadFile,
    upload_session_id: str,
    chunk_index: int = Path(ge=0),
    content_range: str | None = Header(default=None, alias="Content-Range"),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    if content_range is None:
        raise validation_error("Missing Content-Range header")

    content = await upload_file.read()
    service = UploadService(db)
    data = service.upload_chunk(
        session_id=upload_session_id,
        chunk_index=chunk_index,
        content_range=content_range,
        content=content,
        actor_user_id=principal["user"].id,
    )
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/uploads/{upload_session_id}/finalize")
def upload_finalize(
    payload: UploadFinalizeRequest,
    upload_session_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    if idempotency_key is None or not idempotency_key.strip():
        raise validation_error("Missing Idempotency-Key header")

    service = UploadService(db)
    data = service.finalize_upload(
        session_id=upload_session_id,
        idempotency_key=idempotency_key.strip(),
        registration_id=payload.registration_id,
        checklist_id=payload.checklist_id,
        status_label=payload.status_label,
        correction_reason=payload.correction_reason,
        actor_user_id=principal["user"].id,
    )
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.get("/registrations/{registration_id}/materials")
def list_materials(
    registration_id: int = Path(gt=0),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    service = UploadService(db)
    data = service.list_materials(registration_id=registration_id, actor_user_id=principal["user"].id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.get("/registrations/{registration_id}/materials/{material_item_id}/history")
def material_history(
    registration_id: int = Path(gt=0),
    material_item_id: int = Path(gt=0),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    service = UploadService(db)
    data = service.material_history(
        registration_id=registration_id,
        material_item_id=material_item_id,
        actor_user_id=principal["user"].id,
    )
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}
