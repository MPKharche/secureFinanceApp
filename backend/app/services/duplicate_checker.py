"""Duplicate checker service for SMS transactions."""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction


async def check_duplicate(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    amount: Decimal,
    transaction_date: date,
    account_id: Optional[uuid.UUID] = None,
    tolerance_days: int = 2,
    amount_tolerance: Decimal = Decimal("0.01"),
) -> Optional[Transaction]:
    """
    Check for potential duplicate transaction.
    
    Matches transactions within:
    - Same workspace
    - ±tolerance_days of transaction_date
    - Same amount (within tolerance)
    - Same account (if provided)
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        amount: Transaction amount
        transaction_date: Transaction date
        account_id: Optional account ID for stricter matching
        tolerance_days: Days before/after to search
        amount_tolerance: Amount difference tolerance
    
    Returns:
        Matching transaction if found, None otherwise
    """
    # Calculate date range
    date_start = transaction_date - timedelta(days=tolerance_days)
    date_end = transaction_date + timedelta(days=tolerance_days)
    
    # Build query
    query = select(Transaction).where(
        and_(
            Transaction.workspace_id == workspace_id,
            Transaction.date >= date_start,
            Transaction.date <= date_end,
            Transaction.amount >= (amount - amount_tolerance),
            Transaction.amount <= (amount + amount_tolerance),
        )
    )
    
    if account_id:
        query = query.where(Transaction.account_id == account_id)
    
    query = query.order_by(Transaction.date.desc()).limit(1)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()
