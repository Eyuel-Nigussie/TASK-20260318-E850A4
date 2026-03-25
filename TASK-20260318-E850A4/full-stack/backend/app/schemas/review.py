from pydantic import BaseModel, Field


class ReviewTransitionRequest(BaseModel):
    action: str = Field(min_length=3, max_length=32)
    to_state: str = Field(min_length=3, max_length=32)
    comment: str | None = Field(default=None, max_length=2000)


class BatchReviewItem(BaseModel):
    registration_id: int = Field(gt=0)
    row_version: int = Field(gt=0)


class BatchReviewTransitionRequest(BaseModel):
    action: str = Field(min_length=3, max_length=32)
    to_state: str = Field(min_length=3, max_length=32)
    comment: str | None = Field(default=None, max_length=2000)
    items: list[BatchReviewItem] = Field(min_length=1, max_length=50)
