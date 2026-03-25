from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReviewWorkflowRecord(Base):
    __tablename__ = "review_workflow_records"
    __table_args__ = (UniqueConstraint("registration_form_id", "idempotency_key", name="uq_review_idempotency"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_form_id: Mapped[int] = mapped_column(ForeignKey("registration_forms.id"), nullable=False)
    from_state: Mapped[str] = mapped_column(String(32), nullable=False)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
