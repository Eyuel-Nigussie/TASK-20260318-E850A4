from pydantic import BaseModel, Field


class FundingAccountCreateRequest(BaseModel):
    activity_id: int = Field(gt=0)
    account_code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=128)


class FundingTransactionCreateRequest(BaseModel):
    activity_id: int = Field(gt=0)
    funding_account_id: int = Field(gt=0)
    tx_type: str = Field(pattern="^(INCOME|EXPENSE)$")
    category: str = Field(min_length=1, max_length=64)
    amount: float = Field(gt=0)
    occurred_at: str
    note: str | None = Field(default=None, max_length=2000)
    invoice_upload_session_id: str | None = None


class ConfirmOverrunRequest(BaseModel):
    confirm: bool = True
