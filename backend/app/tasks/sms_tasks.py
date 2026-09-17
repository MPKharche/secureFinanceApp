"""Celery tasks for SMS processing."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from celery import Task
from sqlalchemy import select

from app.models.sms_log import SMSLog
from app.models.transaction import Transaction
from app.models.account import Account
from app.services.sms_parser import parse_sms_with_llm
from app.services.duplicate_checker import check_duplicate
from app.services.category_learning import get_category_for_merchant
from app.services.review_queue import add_to_review_queue
from app.worker import celery_app
from app.core.database import async_session_maker


class SMSProcessorTask(Task):
    """Base task with retry configuration."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True  # Exponential backoff


@celery_app.task(bind=True, base=SMSProcessorTask, name="app.tasks.sms_tasks.process_sms_task")
def process_sms_task(self, sms_log_id: str):
    """
    Process SMS message: parse, check duplicates, learn categories, create transaction.
    
    5-step flow:
    1. Parse SMS with LLM
    2. Check confidence (< 0.5 → review queue)
    3. Check for duplicates
    4. Lookup/learn merchant category
    5. Create transaction or add to review queue
    
    Args:
        sms_log_id: SMS log ID (string UUID)
    """
    import asyncio
    
    # Run async processing
    asyncio.run(_process_sms_async(uuid.UUID(sms_log_id)))


async def _process_sms_async(sms_log_id: uuid.UUID):
    """Async SMS processing logic."""
    async with async_session_maker() as db:
        # Fetch SMS log
        result = await db.execute(
            select(SMSLog).where(SMSLog.id == sms_log_id)
        )
        sms_log = result.scalar_one_or_none()
        
        if not sms_log:
            raise ValueError(f"SMS log {sms_log_id} not found")
        
        try:
            # Update status to processing
            sms_log.processing_status = "processing"
            await db.commit()
            
            # Step 1: Parse SMS with LLM
            parse_result = await parse_sms_with_llm(
                sender=sms_log.sender,
                body=sms_log.body,
                user_id=str(sms_log.user_id),
            )
            
            # Store parsed data and confidence
            sms_log.parsed_data = parse_result.to_dict()
            sms_log.confidence = parse_result.confidence
            
            # Step 2: Check confidence
            if not parse_result.success or parse_result.confidence < 0.5:
                # Low confidence or parse failure → review queue
                await add_to_review_queue(
                    db=db,
                    workspace_id=sms_log.workspace_id,
                    user_id=sms_log.user_id,
                    sms_log_id=sms_log.id,
                    review_type="low_confidence" if parse_result.confidence < 0.5 else "failed_parse",
                    review_data={
                        "error": parse_result.error,
                        "confidence": parse_result.confidence,
                        "parsed_data": parse_result.to_dict(),
                    },
                )
                
                sms_log.processing_status = "completed"
                sms_log.processed = True
                await db.commit()
                return
            
            # Parse transaction date
            try:
                transaction_date = datetime.fromisoformat(parse_result.date).date()
            except Exception:
                transaction_date = datetime.now(timezone.utc).date()
            
            # Step 3: Check for duplicates
            # First, try to find matching account based on last digits
            account = await _find_account_by_last_digits(
                db, sms_log.workspace_id, parse_result.account_last_digits
            )
            
            duplicate = await check_duplicate(
                db=db,
                workspace_id=sms_log.workspace_id,
                amount=parse_result.amount,
                transaction_date=transaction_date,
                account_id=account.id if account else None,
            )
            
            if duplicate:
                # Duplicate found → review queue
                await add_to_review_queue(
                    db=db,
                    workspace_id=sms_log.workspace_id,
                    user_id=sms_log.user_id,
                    sms_log_id=sms_log.id,
                    review_type="duplicate",
                    review_data={
                        "duplicate_transaction_id": str(duplicate.id),
                        "parsed_data": parse_result.to_dict(),
                    },
                )
                
                sms_log.processing_status = "completed"
                sms_log.processed = True
                await db.commit()
                return
            
            # Step 4: Lookup merchant category
            category_id = None
            if parse_result.merchant:
                category_id = await get_category_for_merchant(
                    db=db,
                    workspace_id=sms_log.workspace_id,
                    merchant=parse_result.merchant,
                )
            
            # If no learned category, use category hint or mark for review
            if not category_id:
                # Add to review queue for categorization
                await add_to_review_queue(
                    db=db,
                    workspace_id=sms_log.workspace_id,
                    user_id=sms_log.user_id,
                    sms_log_id=sms_log.id,
                    review_type="uncategorized",
                    review_data={
                        "merchant": parse_result.merchant,
                        "category_hint": parse_result.category_hint,
                        "parsed_data": parse_result.to_dict(),
                    },
                )
                
                sms_log.processing_status = "completed"
                sms_log.processed = True
                await db.commit()
                return
            
            # Step 5: Create transaction
            if not account:
                # No account found - need manual review
                await add_to_review_queue(
                    db=db,
                    workspace_id=sms_log.workspace_id,
                    user_id=sms_log.user_id,
                    sms_log_id=sms_log.id,
                    review_type="failed_parse",
                    review_data={
                        "error": "No matching account found",
                        "account_last_digits": parse_result.account_last_digits,
                        "parsed_data": parse_result.to_dict(),
                    },
                )
                
                sms_log.processing_status = "completed"
                sms_log.processed = True
                await db.commit()
                return
            
            transaction = Transaction(
                user_id=sms_log.user_id,
                workspace_id=sms_log.workspace_id,
                account_id=account.id,
                category_id=category_id,
                description=parse_result.description or f"{parse_result.merchant} - SMS",
                amount=parse_result.amount if parse_result.transaction_type == "credit" else -parse_result.amount,
                currency=parse_result.currency or "INR",
                date=transaction_date,
                effective_date=transaction_date,
                type=parse_result.transaction_type,
                source="sms",
                status="posted",
                payee=parse_result.merchant,
            )
            
            db.add(transaction)
            await db.flush()
            
            # Link transaction to SMS log
            sms_log.transaction_id = transaction.id
            sms_log.processing_status = "completed"
            sms_log.processed = True
            
            await db.commit()
            
        except Exception as e:
            # Error occurred - mark as failed
            sms_log.processing_status = "failed"
            sms_log.error_message = str(e)
            await db.commit()
            raise


async def _find_account_by_last_digits(db, workspace_id: uuid.UUID, last_digits: str) -> Account:
    """Find account by last 4 digits."""
    if not last_digits or len(last_digits) < 4:
        return None
    
    # Try to match account number or masked number
    result = await db.execute(
        select(Account).where(
            Account.workspace_id == workspace_id,
            Account.number.like(f"%{last_digits}"),
        ).limit(1)
    )
    
    return result.scalar_one_or_none()
