"""SMS Review Queue model for manual review items."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SMSReviewQueue(Base):
    """
    Queue for SMS transactions that need manual review.
    
    Review types:
    - duplicate: Potential duplicate with existing transaction
    - uncategorized: Merchant has no learned category
    - failed_parse: LLM failed to parse SMS
    - low_confidence: Parse confidence below threshold
    """
    
    __tablename__ = "sms_review_queue"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Link to SMS log
    sms_log_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sms_logs.id"),
        nullable=False,
        index=True,
    )
    
    # Review metadata
    review_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )  # duplicate, uncategorized, failed_parse, low_confidence
    
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, approved, rejected, merged
    
    review_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Resolution
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    def __repr__(self):
        return f"<SMSReviewQueue {self.id} - {self.review_type} ({self.status})>"
