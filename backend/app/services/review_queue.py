"""Review queue service for manual SMS transaction review."""

import uuid
from datetime import datetime, timezone
from typing import List, Literal, Optional

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sms_review_queue import SMSReviewQueue
from app.models.sms_log import SMSLog


ReviewType = Literal["duplicate", "uncategorized", "failed_parse", "low_confidence"]
ReviewStatus = Literal["pending", "approved", "rejected", "merged"]


async def add_to_review_queue(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    sms_log_id: uuid.UUID,
    review_type: ReviewType,
    review_data: dict,
) -> SMSReviewQueue:
    """
    Add SMS to review queue.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        user_id: User ID
        sms_log_id: SMS log ID
        review_type: Type of review needed
        review_data: Context data for the review (e.g., duplicate candidates, parse errors)
        
    Returns:
        Created SMSReviewQueue instance
    """
    review_item = SMSReviewQueue(
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
    status: Optional[ReviewStatus] = None,
    review_type: Optional[ReviewType] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[SMSReviewQueue]:
    """
    Get review queue items.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        status: Optional filter by status (default: pending)
        review_type: Optional filter by review type
        limit: Maximum items to return
        offset: Offset for pagination
        
    Returns:
        List of review queue items
    """
    conditions = [SMSReviewQueue.workspace_id == workspace_id]
    
    if status:
        conditions.append(SMSReviewQueue.status == status)
    else:
        # Default to pending items
        conditions.append(SMSReviewQueue.status == "pending")
    
    if review_type:
        conditions.append(SMSReviewQueue.review_type == review_type)
    
    query = (
        select(SMSReviewQueue)
        .where(and_(*conditions))
        .order_by(SMSReviewQueue.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return list(items)


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
        resolved_by: User ID who resolved it
        resolution_notes: Optional notes about the resolution
        
    Returns:
        Updated SMSReviewQueue instance
    """
    now = datetime.now(timezone.utc)
    
    await db.execute(
        update(SMSReviewQueue)
        .where(SMSReviewQueue.id == review_id)
        .values(
            status="approved",
            resolved_by=resolved_by,
            resolved_at=now,
            resolution_notes=resolution_notes,
        )
    )
    
    await db.commit()
    
    # Fetch updated item
    result = await db.execute(
        select(SMSReviewQueue).where(SMSReviewQueue.id == review_id)
    )
    item = result.scalar_one()
    
    return item


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
        resolved_by: User ID who resolved it
        resolution_notes: Optional notes about the rejection
        
    Returns:
        Updated SMSReviewQueue instance
    """
    now = datetime.now(timezone.utc)
    
    await db.execute(
        update(SMSReviewQueue)
        .where(SMSReviewQueue.id == review_id)
        .values(
            status="rejected",
            resolved_by=resolved_by,
            resolved_at=now,
            resolution_notes=resolution_notes,
        )
    )
    
    await db.commit()
    
    # Fetch updated item
    result = await db.execute(
        select(SMSReviewQueue).where(SMSReviewQueue.id == review_id)
    )
    item = result.scalar_one()
    
    return item


async def merge_duplicate(
    db: AsyncSession,
    review_id: uuid.UUID,
    resolved_by: uuid.UUID,
    keep_transaction_id: uuid.UUID,
    resolution_notes: Optional[str] = None,
) -> SMSReviewQueue:
    """
    Mark a duplicate as merged.
    
    Args:
        db: Database session
        review_id: Review queue item ID
        resolved_by: User ID who resolved it
        keep_transaction_id: Transaction ID to keep
        resolution_notes: Optional notes about the merge
        
    Returns:
        Updated SMSReviewQueue instance
    """
    now = datetime.now(timezone.utc)
    
    # Update review item
    await db.execute(
        update(SMSReviewQueue)
        .where(SMSReviewQueue.id == review_id)
        .values(
            status="merged",
            resolved_by=resolved_by,
            resolved_at=now,
            resolution_notes=resolution_notes or f"Merged with transaction {keep_transaction_id}",
        )
    )
    
    # Update SMS log to link to the kept transaction
    review = await db.execute(
        select(SMSReviewQueue).where(SMSReviewQueue.id == review_id)
    )
    review_item = review.scalar_one()
    
    await db.execute(
        update(SMSLog)
        .where(SMSLog.id == review_item.sms_log_id)
        .values(
            transaction_id=keep_transaction_id,
            processing_status="completed",
        )
    )
    
    await db.commit()
    
    # Fetch updated review item
    result = await db.execute(
        select(SMSReviewQueue).where(SMSReviewQueue.id == review_id)
    )
    item = result.scalar_one()
    
    return item
