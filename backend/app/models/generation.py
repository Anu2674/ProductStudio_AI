from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    source_image_id: Mapped[int] = mapped_column(Integer, ForeignKey("images.id"), nullable=False)
    generation_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    prompt: Mapped[str | None] = mapped_column(String, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(String, nullable=True)
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_storage_path: Mapped[str | None] = mapped_column(String, nullable=True)
    quality_score: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
