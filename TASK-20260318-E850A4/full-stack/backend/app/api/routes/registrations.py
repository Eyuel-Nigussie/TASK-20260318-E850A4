from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import get_request_id
from app.core.database import get_db
from app.schemas.common import MetaInfo
from app.schemas.registration import RegistrationCreateRequest, RegistrationSupplementRequest
from app.security.authz import get_current_user
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/registrations", tags=["registrations"])


@router.post("")
def create_registration(
    payload: RegistrationCreateRequest,
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    service = RegistrationService(db)
    data = service.create_registration(
        activity_id=payload.activity_id,
        form_payload=payload.form_payload,
        applicant_user_id=principal["user"].id,
    )
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.get("/me")
def list_my_registrations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    activity_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    service = RegistrationService(db)
    data = service.list_my_registrations(
        applicant_user_id=principal["user"].id,
        page=page,
        page_size=page_size,
        activity_id=activity_id,
        status=status,
    )
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.get("/{registration_id}")
def get_registration(
    registration_id: int = Path(gt=0),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    service = RegistrationService(db)
    data = service.get_registration(registration_id=registration_id, requester_user_id=principal["user"].id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/{registration_id}/submit")
def submit_registration(
    registration_id: int = Path(gt=0),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    service = RegistrationService(db)
    data = service.submit(registration_id=registration_id, requester_user_id=principal["user"].id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/{registration_id}/supplement")
def supplement_registration(
    payload: RegistrationSupplementRequest,
    registration_id: int = Path(gt=0),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    service = RegistrationService(db)
    data = service.supplement(
        registration_id=registration_id,
        requester_user_id=principal["user"].id,
        reason=payload.reason,
    )
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}
