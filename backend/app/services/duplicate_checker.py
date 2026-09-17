"""Duplicate detection service for SMS transactions."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction


async def check_duplicate(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    amount: Decimal,
    transaction_date: date,
    account_id: Optional[uuid.UUID] = None,
) -> Optional[Transaction]:
    """
    Check for duplicate transactions using strict matching.
    
    Strategy: same amount + same day + same account (if provided)
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        amount: Transaction amount
        transaction_date: Transaction date
        account_id: Optional account ID for stricter matching
        
    Returns:
        Matching Transaction if found, None otherwise
    """
    # Build query conditions
    conditions = [
        Transaction.workspace_id == workspace_id,
        Transaction.amount == abs(amount),  # Compare absolute values
        Transaction.date == transaction_date,
    ]
    
    if account_id:
        conditions.append(Transaction.account_id == account_id)
    
    # Query for matching transaction
    query = select(Transaction).where(and_(*conditions)).limit(1)
    result = await db.execute(query)
    duplicate = result.scalar_one_or_none()
    
    return duplicate


async def check_duplicate_fuzzy(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    amount: Decimal,
    transaction_date: date,
    merchant: Optional[str] = None,
    tolerance_amount: Decimal = Decimal("0.01"),
    tolerance_days: int = 1,
) -> list[Transaction]:
    """
    Check for potential duplicates with fuzzy matching.
    
    Finds transactions within tolerance window (amount +/- tolerance, date +/- days).
    Used for review queue to flag potential duplicates for manual review.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        amount: Transaction amount
        transaction_date: Transaction date
        merchant: Optional merchant name for additional matching
        tolerance_amount: Amount tolerance (default 0.01)
        tolerance_days: Days tolerance (default 1 day)
        
    Returns:
        List of potential duplicate transactions
    """
    amount_min = abs(amount) - tolerance_amount
    amount_max = abs(amount) + tolerance_amount
    date_min = transaction_date - timedelta(days=tolerance_days)
    date_max = transaction_date + timedelta(days=tolerance_days)
    
    # Build query
    conditions = [
        Transaction.workspace_id == workspace_id,
        Transaction.amount >= amount_min,
        Transaction.amount <= amount_max,
        Transaction.date >= date_min,
        Transaction.date <= date_max,
    ]
    
    # Add merchant matching if provided
    if merchant:
        # Simple contains match (could be enhanced with fuzzy string matching)
        conditions.append(Transaction.description.ilike(f"%{merchant}%"))
    
    query = select(Transaction).where(and_(*conditions)).limit(5)
    result = await db.execute(query)
    duplicates = result.scalars().all()
    
    return list(duplicates)
