from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DataCollectionBatch(Base):
    __tablename__ = "data_collection_batches"
    __table_args__ = (UniqueConstraint("activity_id", "batch_code", name="uq_collection_batch_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), nullable=False)
    batch_code: Mapped[str] = mapped_column(String(64), nullable=False)
    source_scope: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    whitelist_policy: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
