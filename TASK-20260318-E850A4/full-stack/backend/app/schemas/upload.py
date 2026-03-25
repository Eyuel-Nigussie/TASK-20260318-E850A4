from pydantic import BaseModel, Field


class UploadInitRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=3, max_length=128)
    size_bytes: int = Field(gt=0, le=20971520)


class UploadInitResponse(BaseModel):
    upload_session_id: str
    max_chunk_size: int
    expires_at: str


class UploadFinalizeRequest(BaseModel):
    registration_id: int
    checklist_id: int
    status_label: str = Field(pattern="^(PENDING_SUBMISSION|SUBMITTED|NEEDS_CORRECTION)$")
    correction_reason: str | None = None


class UploadFinalizeResponse(BaseModel):
    material_item_id: int
    new_version_no: int
    sha256: str
    size_bytes: int
    total_material_size_bytes: int
