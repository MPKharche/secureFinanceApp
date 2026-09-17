"""Schemas for SMS auto-capture endpoints."""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class SMSIngestRequest(BaseModel):
    """Request body for SMS ingest endpoint."""
    
    sender: str = Field(..., min_length=1, max_length=50, description="SMS sender (e.g., HDFCBK)")
    body: str = Field(..., min_length=1, max_length=5000, description="SMS message body")
    received_at: datetime = Field(..., description="Timestamp when SMS was received on device")


class SMSIngestResponse(BaseModel):
    """Response for SMS ingest endpoint."""
    
    success: bool
    message: str
    sms_log_id: Optional[uuid.UUID] = None


class SMSReviewQueueItem(BaseModel):
    """Review queue item."""
    
    id: uuid.UUID
    sms_log_id: uuid.UUID
    review_type: str
    status: str
    review_data: dict
    resolution_notes: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    
    # SMS log details
    sender: Optional[str] = None
    body: Optional[str] = None
    parsed_data: Optional[dict] = None
    
    class Config:
        from_attributes = True


class ReviewActionRequest(BaseModel):
    """Request body for review actions."""
    
    resolution_notes: Optional[str] = Field(None, max_length=500)


class MergeActionRequest(BaseModel):
    """Request body for merge duplicate action."""
    
    keep_transaction_id: uuid.UUID
    resolution_notes: Optional[str] = Field(None, max_length=500)


class ApproveUncategorizedRequest(BaseModel):
    """Request body for approving uncategorized merchant."""
    
    category_id: uuid.UUID
    resolution_notes: Optional[str] = Field(None, max_length=500)
