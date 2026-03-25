from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MaterialVersion(Base):
    __tablename__ = "material_versions"
    __table_args__ = (
        UniqueConstraint("material_item_id", "version_no", name="uq_material_item_version_no"),
        CheckConstraint("version_no BETWEEN 1 AND 3", name="ck_material_version_no"),
        CheckConstraint(
            "status_label IN ('PENDING_SUBMISSION','SUBMITTED','NEEDS_CORRECTION')",
            name="ck_material_version_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_item_id: Mapped[int] = mapped_column(ForeignKey("material_items.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status_label: Mapped[str] = mapped_column(String(32), nullable=False)
    file_blob_id: Mapped[int] = mapped_column(ForeignKey("file_blobs.id"), nullable=False)
    correction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
