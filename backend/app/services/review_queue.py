"""Review queue service for SMS transaction manual review."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sms_review_queue import SMSReviewQueue


async def add_to_review_queue(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    sms_log_id: uuid.UUID,
    review_type: str,
    review_data: dict,
) -> SMSReviewQueue:
    """
    Add SMS to review queue.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        user_id: User ID
        sms_log_id: SMS log ID
        review_type: Type of review (duplicate, uncategorized, failed_parse, low_confidence)
        review_data: Additional data for review
    
    Returns:
        Created review queue item
    """
    review_item = SMSReviewQueue(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        user_id=user_id,
        sms_log_id=sms_log_id,
        review_type=review_type,
        status="pending",
        review_data=review_data,
    )
    
    db.add(review_item)
    await db.commit()
    await db.refresh(review_item)
    
    return review_item


async def get_review_queue(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    status: Optional[str] = "pending",
    review_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[SMSReviewQueue]:
    """
    Get review queue items for workspace.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        status: Filter by status
        review_type: Filter by review type
        limit: Max results
        offset: Pagination offset
    
    Returns:
        List of review queue items
    """
    query = select(SMSReviewQueue).where(
        SMSReviewQueue.workspace_id == workspace_id
    )
    
    if status:
        query = query.where(SMSReviewQueue.status == status)
    
    if review_type:
        query = query.where(SMSReviewQueue.review_type == review_type)
    
    query = query.order_by(SMSReviewQueue.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    return result.scalars().all()


async def approve_review_item(
    db: AsyncSession,
    review_id: uuid.UUID,
    resolved_by: uuid.UUID,
    resolution_notes: Optional[str] = None,
) -> SMSReviewQueue:
    """
    Approve a review queue item.
    
    Args:
        db: Database session
        review_id: Review queue item ID
        resolved_by: User ID resolving the review
        resolution_notes: Optional notes
    
    Returns:
        Updated review queue item
    """
    result = await db.execute(
        select(SMSReviewQueue).where(SMSReviewQueue.id == review_id)
    )
    review_item = result.scalar_one()
    
    review_item.status = "approved"
    review_item.resolved_by = resolved_by
    review_item.resolution_notes = resolution_notes
    review_item.resolved_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(review_item)
    
    return review_item


async def reject_review_item(
    db: AsyncSession,
    review_id: uuid.UUID,
    resolved_by: uuid.UUID,
    resolution_notes: Optional[str] = None,
) -> SMSReviewQueue:
    """
    Reject a review queue item.
    
    Args:
        db: Database session
        review_id: Review queue item ID
        resolved_by: User ID resolving the review
        resolution_notes: Optional notes
    
    Returns:
        Updated review queue item
    """
    result = await db.execute(
        select(SMSReviewQueue).where(SMSReviewQueue.id == review_id)
    )
    review_item = result.scalar_one()
    
    review_item.status = "rejected"
    review_item.resolved_by = resolved_by
    review_item.resolution_notes = resolution_notes
    review_item.resolved_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(review_item)
    
    return review_item


async def merge_duplicate(
    db: AsyncSession,
    review_id: uuid.UUID,
    resolved_by: uuid.UUID,
    keep_transaction_id: uuid.UUID,
    resolution_notes: Optional[str] = None,
) -> SMSReviewQueue:
    """
    Merge duplicate transaction - link SMS to existing transaction.
    
    Args:
        db: Database session
        review_id: Review queue item ID
        resolved_by: User ID resolving the review
        keep_transaction_id: Transaction ID to keep
        resolution_notes: Optional notes
    
    Returns:
        Updated review queue item
    """
    result = await db.execute(
        select(SMSReviewQueue).where(SMSReviewQueue.id == review_id)
    )
    review_item = result.scalar_one()
    
    # Link SMS log to the kept transaction
    from app.models.sms_log import SMSLog
    sms_result = await db.execute(
        select(SMSLog).where(SMSLog.id == review_item.sms_log_id)
    )
    sms_log = sms_result.scalar_one()
    sms_log.transaction_id = keep_transaction_id
    
    # Mark review as merged
    review_item.status = "merged"
    review_item.resolved_by = resolved_by
    review_item.resolution_notes = resolution_notes or f"Merged with transaction {keep_transaction_id}"
    review_item.resolved_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(review_item)
    
    return review_item
