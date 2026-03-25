from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FundingTransaction(Base):
    __tablename__ = "funding_transactions"
    __table_args__ = (
        UniqueConstraint("activity_id", "idempotency_key", name="uq_funding_tx_idempotency"),
        CheckConstraint("tx_type IN ('INCOME','EXPENSE')", name="ck_funding_tx_type"),
        CheckConstraint("tx_status IN ('CONFIRMED','PENDING_CONFIRMATION')", name="ck_funding_tx_status"),
        CheckConstraint("amount > 0", name="ck_funding_tx_amount"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), nullable=False)
    funding_account_id: Mapped[int] = mapped_column(ForeignKey("funding_accounts.id"), nullable=False)
    tx_status: Mapped[str] = mapped_column(String(32), nullable=False)
    tx_type: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_file_blob_id: Mapped[int | None] = mapped_column(ForeignKey("file_blobs.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
