from pydantic import BaseModel, Field


class MetaInfo(BaseModel):
    request_id: str = Field(default="")


class ErrorInfo(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)
    request_id: str = Field(default="")


class SuccessResponse(BaseModel):
    success: bool = True
    data: dict
    meta: MetaInfo


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorInfo
