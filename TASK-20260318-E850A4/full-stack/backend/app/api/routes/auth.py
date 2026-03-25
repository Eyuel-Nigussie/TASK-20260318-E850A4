from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_request_id
from app.core.database import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest
from app.schemas.common import MetaInfo
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, request: Request, request_id: str = Depends(get_request_id), db: Session = Depends(get_db)):
    service = AuthService(db)
    data = service.login(payload.username, payload.password, request, request_id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/refresh")
def refresh(payload: RefreshRequest, request_id: str = Depends(get_request_id), db: Session = Depends(get_db)):
    service = AuthService(db)
    data = service.refresh(payload.refresh_token)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/register")
def register(payload: RegisterRequest, request: Request, request_id: str = Depends(get_request_id), db: Session = Depends(get_db)):
    service = AuthService(db)
    data = service.register(
        email=payload.email,
        password=payload.password,
        confirm_password=payload.confirm_password,
        request=request,
        request_id=request_id,
    )
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/logout")
def logout(request_id: str = Depends(get_request_id)):
    return {"success": True, "data": {"logged_out": True}, "meta": MetaInfo(request_id=request_id).model_dump()}
