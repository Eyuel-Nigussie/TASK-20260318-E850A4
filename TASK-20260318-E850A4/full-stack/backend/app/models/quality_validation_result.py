from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QualityValidationResult(Base):
    __tablename__ = "quality_validation_results"
    __table_args__ = (
        CheckConstraint("approval_rate BETWEEN 0 AND 1", name="ck_quality_approval_rate"),
        CheckConstraint("correction_rate BETWEEN 0 AND 1", name="ck_quality_correction_rate"),
        CheckConstraint("overspending_rate >= 0", name="ck_quality_overspending_rate"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    approval_rate: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    correction_rate: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    overspending_rate: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    metrics_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
