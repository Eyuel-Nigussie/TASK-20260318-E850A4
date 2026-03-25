import uuid

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.database import get_db


def db_session() -> Session:
    return Depends(get_db)


def get_request_id(x_request_id: str | None = Header(default=None)) -> str:
    return x_request_id or f"req_{uuid.uuid4().hex}"


def get_client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
