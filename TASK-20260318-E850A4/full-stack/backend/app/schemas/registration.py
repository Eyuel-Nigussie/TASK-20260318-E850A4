from pydantic import BaseModel, Field


class RegistrationCreateRequest(BaseModel):
    activity_id: int = Field(gt=0)
    form_payload: dict = Field(default_factory=dict)


class RegistrationSupplementRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)
