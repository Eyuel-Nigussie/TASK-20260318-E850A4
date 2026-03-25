from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MaterialItem(Base):
    __tablename__ = "material_items"
    __table_args__ = (
        UniqueConstraint("registration_form_id", "checklist_id", name="uq_material_item_registration_checklist"),
        CheckConstraint("version_count >= 0 AND version_count <= 3", name="ck_material_item_version_count"),
        CheckConstraint(
            "latest_label IN ('PENDING_SUBMISSION','SUBMITTED','NEEDS_CORRECTION')",
            name="ck_material_item_latest_label",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_form_id: Mapped[int] = mapped_column(ForeignKey("registration_forms.id"), nullable=False)
    checklist_id: Mapped[int] = mapped_column(ForeignKey("material_checklists.id"), nullable=False)
    latest_label: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_SUBMISSION")
    version_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
