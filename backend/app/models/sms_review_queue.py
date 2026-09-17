import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.sms_log import SMSLog
    from app.models.user import User
    from app.models.workspace import Workspace


class SMSReviewQueue(Base):
    __tablename__ = "sms_review_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    sms_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sms_logs.id", ondelete="CASCADE"), nullable=False
    )
    review_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # duplicate, uncategorized, failed_parse, low_confidence
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", nullable=False
    )  # pending, approved, rejected, merged
    review_data: Mapped[dict] = mapped_column(JSON, nullable=False)  # Context for review (e.g., duplicate candidates)
    resolution_notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship()
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    sms_log: Mapped["SMSLog"] = relationship()
    resolver: Mapped[Optional["User"]] = relationship(foreign_keys=[resolved_by])

    __table_args__ = (
        Index("idx_sms_review_queue_workspace_status", "workspace_id", "status"),
        Index("idx_sms_review_queue_user_status", "user_id", "status"),
    )
