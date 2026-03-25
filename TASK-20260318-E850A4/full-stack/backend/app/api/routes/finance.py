from fastapi import APIRouter, Depends, Header, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import get_request_id
from app.core.database import get_db
from app.core.errors import forbidden, validation_error
from app.schemas.common import MetaInfo
from app.schemas.finance import ConfirmOverrunRequest, FundingAccountCreateRequest, FundingTransactionCreateRequest
from app.security.authz import get_current_user
from app.services.finance_service import FinanceService

router = APIRouter(prefix="/finance", tags=["finance"])


def _ensure_finance_role(principal: dict) -> None:
    role_code = principal["role"].code
    if role_code not in {"FINANCIAL_ADMIN", "SYSTEM_ADMIN"}:
        raise forbidden("Financial admin permission required")


@router.post("/accounts")
def create_account(
    payload: FundingAccountCreateRequest,
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_finance_role(principal)
    service = FinanceService(db)
    data = service.create_account(activity_id=payload.activity_id, account_code=payload.account_code, name=payload.name)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.get("/accounts")
def list_accounts(
    activity_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_finance_role(principal)
    service = FinanceService(db)
    data = service.list_accounts(activity_id=activity_id, page=page, page_size=page_size)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/transactions")
def create_transaction(
    payload: FundingTransactionCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_finance_role(principal)
    if not idempotency_key or not idempotency_key.strip():
        raise validation_error("Missing Idempotency-Key header")

    service = FinanceService(db)
    data = service.create_transaction(
        activity_id=payload.activity_id,
        funding_account_id=payload.funding_account_id,
        tx_type=payload.tx_type,
        category=payload.category,
        amount=payload.amount,
        occurred_at=payload.occurred_at,
        note=payload.note,
        invoice_upload_session_id=payload.invoice_upload_session_id,
        created_by=principal["user"].id,
        idempotency_key=idempotency_key.strip(),
    )
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.post("/transactions/{transaction_id}/confirm-overrun")
def confirm_overrun(
    payload: ConfirmOverrunRequest,
    transaction_id: int = Path(gt=0),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_finance_role(principal)
    if not payload.confirm:
        raise validation_error("Confirmation flag must be true")

    service = FinanceService(db)
    data = service.confirm_overrun(transaction_id=transaction_id, actor_user_id=principal["user"].id)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.get("/transactions")
def list_transactions(
    activity_id: int = Query(...),
    tx_type: str | None = Query(default=None),
    category: str | None = Query(default=None),
    from_dt: str | None = Query(default=None, alias="from"),
    to_dt: str | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_finance_role(principal)
    service = FinanceService(db)
    data = service.list_transactions(
        activity_id=activity_id,
        tx_type=tx_type,
        category=category,
        from_dt=from_dt,
        to_dt=to_dt,
        page=page,
        page_size=page_size,
    )
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}


@router.get("/statistics")
def statistics(
    activity_id: int = Query(...),
    group_by: str = Query(...),
    from_dt: str | None = Query(default=None, alias="from"),
    to_dt: str | None = Query(default=None, alias="to"),
    principal=Depends(get_current_user),
    request_id: str = Depends(get_request_id),
    db: Session = Depends(get_db),
):
    _ensure_finance_role(principal)
    service = FinanceService(db)
    data = service.statistics(activity_id=activity_id, group_by=group_by, from_dt=from_dt, to_dt=to_dt)
    return {"success": True, "data": data, "meta": MetaInfo(request_id=request_id).model_dump()}
