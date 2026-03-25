from fastapi import APIRouter, Depends, Header, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import get_request_id
from app.core.database import get_db
from app.core.errors import forbidden, validation_error
from app.schemas.common import MetaInfo
from app.schemas.review import BatchReviewTransitionRequest, ReviewTransitionRequest
from app.security.authz import get_current_user
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _ensure_reviewer(principal: dict) -> None:
    role_code = principal["role"].code
    if role_code not in {"REVIEWER", "SYSTEM_ADMIN"}:
        raise forbidden("Reviewer permission required")


@router.get("/queue")
def review_queue(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    activity_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_reviewer(principal)
    service = ReviewService(db)
    data = service.queue(page=page, page_size=page_size, activity_id=activity_id, status=status, keyword=keyword)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/{registration_id}/transition")
def transition(
    payload: ReviewTransitionRequest,
    registration_id: int = Path(gt=0),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    if_match: int | None = Header(default=None, alias="If-Match"),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_reviewer(principal)
    service = ReviewService(db)
    data = service.transition(
        registration_id=registration_id,
        to_state=payload.to_state,
        action=payload.action,
        comment=payload.comment,
        actor_user_id=principal["user"].id,
        idempotency_key=idempotency_key,
        expected_row_version=if_match,
    )
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/batch-transition")
def batch_transition(
    payload: BatchReviewTransitionRequest,
    atomic: bool = Query(default=False),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_reviewer(principal)
    if len(payload.items) > 50:
        raise validation_error("Batch size exceeds 50 items")

    service = ReviewService(db)
    data = service.batch_transition(
        items=[item.model_dump() for item in payload.items],
        to_state=payload.to_state,
        action=payload.action,
        comment=payload.comment,
        actor_user_id=principal["user"].id,
        batch_key=idempotency_key,
        atomic=atomic,
    )
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.get("/{registration_id}/logs")
def review_logs(
    registration_id: int = Path(gt=0),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_reviewer(principal)
    service = ReviewService(db)
    data = service.logs(registration_id=registration_id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}
