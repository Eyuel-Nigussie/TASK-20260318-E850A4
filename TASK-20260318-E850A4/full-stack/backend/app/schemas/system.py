from pydantic import BaseModel, Field


class BackupRestoreRequest(BaseModel):
    backup_id: str = Field(min_length=3, max_length=64)
    confirm: bool
    pre_restore_backup: bool = True


class ProfileUpdateRequest(BaseModel):
    id_number: str | None = Field(default=None, max_length=64)
    contact: str | None = Field(default=None, max_length=64)
