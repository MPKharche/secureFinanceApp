"""API endpoints for SMS auto-capture."""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_writable_workspace
from app.models.sms_log import SMSLog
from app.models.sms_review_queue import SMSReviewQueue
from app.schemas.sms import (
    ApproveUncategorizedRequest,
    MergeActionRequest,
    ReviewActionRequest,
    SMSIngestRequest,
    SMSIngestResponse,
    SMSReviewQueueItem,
)
from app.services.review_queue import (
    approve_review_item,
    get_review_queue,
    merge_duplicate,
    reject_review_item,
)
from app.services.category_learning import learn_merchant_category
from app.tasks.sms_tasks import process_sms_task

router = APIRouter(prefix="/api/sms", tags=["sms"])


# Rate limiting decorator (placeholder - implement with fastapi-limiter or similar)
# For now, basic in-memory rate limiting would be added here
# Target: 100 SMS/min per user


@router.post("/ingest", response_model=SMSIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_sms(
    request: SMSIngestRequest,
    workspace: WorkspaceContext = Depends(current_writable_workspace),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Ingest SMS from Android app.
    
    - Creates SMS log entry
    - Enqueues Celery task for processing
    - Implements idempotency check (sender + body + timestamp)
    - Rate limited to 100 SMS/min per user
    """
    # Idempotency check: same sender + body + received_at
    existing_query = select(SMSLog).where(
        and_(
            SMSLog.workspace_id == workspace.workspace_id,
            SMSLog.sender == request.sender,
            SMSLog.body == request.body,
            SMSLog.received_at == request.received_at,
        )
    )
    result = await db.execute(existing_query)
    existing = result.scalar_one_or_none()
    
    if existing:
        return SMSIngestResponse(
            success=True,
            message="SMS already ingested (duplicate)",
            sms_log_id=existing.id,
        )
    
    # Create SMS log entry
    sms_log = SMSLog(
        user_id=workspace.user_id,
        workspace_id=workspace.workspace_id,
        sender=request.sender,
        body=request.body,
        received_at=request.received_at,
        processed=False,
        processing_status="pending",
    )
    
    db.add(sms_log)
    await db.commit()
    await db.refresh(sms_log)
    
    # Enqueue Celery task for background processing
    process_sms_task.delay(str(sms_log.id))
    
    return SMSIngestResponse(
        success=True,
        message="SMS received and queued for processing",
        sms_log_id=sms_log.id,
    )


@router.get("/review-queue", response_model=List[SMSReviewQueueItem])
async def get_review_queue_endpoint(
    status: Optional[str] = Query("pending", regex="^(pending|approved|rejected|merged)$"),
    review_type: Optional[str] = Query(None, regex="^(duplicate|uncategorized|failed_parse|low_confidence)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    workspace: WorkspaceContext = Depends(current_writable_workspace),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get review queue items for the current workspace.
    
    Returns items that need manual review with SMS log details.
    """
    items = await get_review_queue(
        db=db,
        workspace_id=workspace.workspace_id,
        status=status,
        review_type=review_type,
        limit=limit,
        offset=offset,
    )
    
    # Enrich with SMS log details
    enriched_items = []
    for item in items:
        # Fetch SMS log
        sms_result = await db.execute(
            select(SMSLog).where(SMSLog.id == item.sms_log_id)
        )
        sms_log = sms_result.scalar_one_or_none()
        
        enriched_item = SMSReviewQueueItem(
            id=item.id,
            sms_log_id=item.sms_log_id,
            review_type=item.review_type,
            status=item.status,
            review_data=item.review_data,
            resolution_notes=item.resolution_notes,
            created_at=item.created_at,
            resolved_at=item.resolved_at,
            sender=sms_log.sender if sms_log else None,
            body=sms_log.body if sms_log else None,
            parsed_data=sms_log.parsed_data if sms_log else None,
        )
        enriched_items.append(enriched_item)
    
    return enriched_items


@router.post("/review/{review_id}/approve", response_model=SMSReviewQueueItem)
async def approve_review(
    review_id: uuid.UUID,
    request: ReviewActionRequest,
    workspace: WorkspaceContext = Depends(current_writable_workspace),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Approve a review queue item.
    
    For uncategorized merchants, use the separate endpoint with category_id.
    """
    # Verify review item belongs to workspace
    check_query = select(SMSReviewQueue).where(
        and_(
            SMSReviewQueue.id == review_id,
            SMSReviewQueue.workspace_id == workspace.workspace_id,
        )
    )
    result = await db.execute(check_query)
    review_item = result.scalar_one_or_none()
    
    if not review_item:
        raise HTTPException(status_code=404, detail="Review item not found")
    
    updated = await approve_review_item(
        db=db,
        review_id=review_id,
        resolved_by=workspace.user_id,
        resolution_notes=request.resolution_notes,
    )
    
    # Fetch SMS log for response
    sms_result = await db.execute(
        select(SMSLog).where(SMSLog.id == updated.sms_log_id)
    )
    sms_log = sms_result.scalar_one_or_none()
    
    return SMSReviewQueueItem(
        id=updated.id,
        sms_log_id=updated.sms_log_id,
        review_type=updated.review_type,
        status=updated.status,
        review_data=updated.review_data,
        resolution_notes=updated.resolution_notes,
        created_at=updated.created_at,
        resolved_at=updated.resolved_at,
        sender=sms_log.sender if sms_log else None,
        body=sms_log.body if sms_log else None,
        parsed_data=sms_log.parsed_data if sms_log else None,
    )


@router.post("/review/{review_id}/approve-uncategorized", response_model=SMSReviewQueueItem)
async def approve_uncategorized(
    review_id: uuid.UUID,
    request: ApproveUncategorizedRequest,
    workspace: WorkspaceContext = Depends(current_writable_workspace),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Approve an uncategorized merchant with category selection.
    
    Learns the merchant-category mapping for future transactions.
    """
    # Verify review item
    check_query = select(SMSReviewQueue).where(
        and_(
            SMSReviewQueue.id == review_id,
            SMSReviewQueue.workspace_id == workspace.workspace_id,
            SMSReviewQueue.review_type == "uncategorized",
        )
    )
    result = await db.execute(check_query)
    review_item = result.scalar_one_or_none()
    
    if not review_item:
        raise HTTPException(status_code=404, detail="Review item not found")
    
    # Learn merchant-category mapping
    merchant = review_item.review_data.get("merchant")
    if merchant:
        await learn_merchant_category(
            db=db,
            workspace_id=workspace.workspace_id,
            merchant=merchant,
            category_id=request.category_id,
        )
    
    # Approve the review item
    updated = await approve_review_item(
        db=db,
        review_id=review_id,
        resolved_by=workspace.user_id,
        resolution_notes=request.resolution_notes or f"Categorized as {request.category_id}",
    )
    
    # Fetch SMS log
    sms_result = await db.execute(
        select(SMSLog).where(SMSLog.id == updated.sms_log_id)
    )
    sms_log = sms_result.scalar_one_or_none()
    
    return SMSReviewQueueItem(
        id=updated.id,
        sms_log_id=updated.sms_log_id,
        review_type=updated.review_type,
        status=updated.status,
        review_data=updated.review_data,
        resolution_notes=updated.resolution_notes,
        created_at=updated.created_at,
        resolved_at=updated.resolved_at,
        sender=sms_log.sender if sms_log else None,
        body=sms_log.body if sms_log else None,
        parsed_data=sms_log.parsed_data if sms_log else None,
    )


@router.post("/review/{review_id}/reject", response_model=SMSReviewQueueItem)
async def reject_review(
    review_id: uuid.UUID,
    request: ReviewActionRequest,
    workspace: WorkspaceContext = Depends(current_writable_workspace),
    db: AsyncSession = Depends(get_async_session),
):
    """Reject a review queue item."""
    # Verify review item
    check_query = select(SMSReviewQueue).where(
        and_(
            SMSReviewQueue.id == review_id,
            SMSReviewQueue.workspace_id == workspace.workspace_id,
        )
    )
    result = await db.execute(check_query)
    review_item = result.scalar_one_or_none()
    
    if not review_item:
        raise HTTPException(status_code=404, detail="Review item not found")
    
    updated = await reject_review_item(
        db=db,
        review_id=review_id,
        resolved_by=workspace.user_id,
        resolution_notes=request.resolution_notes,
    )
    
    # Fetch SMS log
    sms_result = await db.execute(
        select(SMSLog).where(SMSLog.id == updated.sms_log_id)
    )
    sms_log = sms_result.scalar_one_or_none()
    
    return SMSReviewQueueItem(
        id=updated.id,
        sms_log_id=updated.sms_log_id,
        review_type=updated.review_type,
        status=updated.status,
        review_data=updated.review_data,
        resolution_notes=updated.resolution_notes,
        created_at=updated.created_at,
        resolved_at=updated.resolved_at,
        sender=sms_log.sender if sms_log else None,
        body=sms_log.body if sms_log else None,
        parsed_data=sms_log.parsed_data if sms_log else None,
    )


@router.post("/review/{review_id}/merge", response_model=SMSReviewQueueItem)
async def merge_duplicate_review(
    review_id: uuid.UUID,
    request: MergeActionRequest,
    workspace: WorkspaceContext = Depends(current_writable_workspace),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Merge duplicate transaction.
    
    Links SMS log to the kept transaction and marks review as merged.
    """
    # Verify review item
    check_query = select(SMSReviewQueue).where(
        and_(
            SMSReviewQueue.id == review_id,
            SMSReviewQueue.workspace_id == workspace.workspace_id,
            SMSReviewQueue.review_type == "duplicate",
        )
    )
    result = await db.execute(check_query)
    review_item = result.scalar_one_or_none()
    
    if not review_item:
        raise HTTPException(status_code=404, detail="Review item not found or not a duplicate")
    
    updated = await merge_duplicate(
        db=db,
        review_id=review_id,
        resolved_by=workspace.user_id,
        keep_transaction_id=request.keep_transaction_id,
        resolution_notes=request.resolution_notes,
    )
    
    # Fetch SMS log
    sms_result = await db.execute(
        select(SMSLog).where(SMSLog.id == updated.sms_log_id)
    )
    sms_log = sms_result.scalar_one_or_none()
    
    return SMSReviewQueueItem(
        id=updated.id,
        sms_log_id=updated.sms_log_id,
        review_type=updated.review_type,
        status=updated.status,
        review_data=updated.review_data,
        resolution_notes=updated.resolution_notes,
        created_at=updated.created_at,
        resolved_at=updated.resolved_at,
        sender=sms_log.sender if sms_log else None,
        body=sms_log.body if sms_log else None,
        parsed_data=sms_log.parsed_data if sms_log else None,
    )
