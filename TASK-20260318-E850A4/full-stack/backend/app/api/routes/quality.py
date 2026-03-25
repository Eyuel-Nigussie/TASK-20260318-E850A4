from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import get_request_id
from app.core.database import get_db
from app.core.errors import forbidden
from app.schemas.common import MetaInfo
from app.security.authz import get_current_user
from app.services.quality_service import QualityService

router = APIRouter(prefix="/quality", tags=["quality"])


def _ensure_quality_access(principal: dict) -> None:
    role_code = principal["role"].code
    if role_code not in {"REVIEWER", "FINANCIAL_ADMIN", "SYSTEM_ADMIN"}:
        raise forbidden("Quality metrics permission required")


@router.post("/compute/{activity_id}")
def compute_quality(
    activity_id: int = Path(gt=0),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_quality_access(principal)
    service = QualityService(db)
    data = service.compute(activity_id=activity_id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.get("/results")
def quality_results(
    activity_id: int = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_quality_access(principal)
    service = QualityService(db)
    data = service.list_results(activity_id=activity_id, page=page, page_size=page_size)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.get("/latest/{activity_id}")
def quality_latest(
    activity_id: int = Path(gt=0),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_quality_access(principal)
    service = QualityService(db)
    data = service.latest(activity_id=activity_id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}
