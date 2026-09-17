"""Category learning service for SMS merchant categorization."""

import uuid
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


# In-memory store for learned merchant-category mappings
# In production, this should be a database table
_MERCHANT_CATEGORY_MAP: dict[tuple[uuid.UUID, str], uuid.UUID] = {}


async def learn_merchant_category(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    merchant: str,
    category_id: uuid.UUID,
) -> None:
    """
    Learn merchant-category mapping for future auto-categorization.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        merchant: Merchant name (normalized)
        category_id: Category ID to associate
    """
    # Verify category exists and belongs to workspace
    result = await db.execute(
        select(Category).where(Category.id == category_id).limit(1)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise ValueError(f"Category {category_id} not found or not accessible")
    
    # Store the mapping
    key = (workspace_id, merchant.lower().strip())
    _MERCHANT_CATEGORY_MAP[key] = category_id


async def get_category_for_merchant(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    merchant: str,
) -> Optional[uuid.UUID]:
    """
    Get learned category for merchant.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        merchant: Merchant name
    
    Returns:
        Category ID if learned, None otherwise
    """
    key = (workspace_id, merchant.lower().strip())
    return _MERCHANT_CATEGORY_MAP.get(key)


async def forget_merchant_category(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    merchant: str,
) -> bool:
    """
    Remove learned merchant-category mapping.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        merchant: Merchant name
    
    Returns:
        True if mapping existed and was removed
    """
    key = (workspace_id, merchant.lower().strip())
    if key in _MERCHANT_CATEGORY_MAP:
        del _MERCHANT_CATEGORY_MAP[key]
        return True
    return False


async def get_all_learned_merchants(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    """
    Get all learned merchant-category mappings for workspace.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
    
    Returns:
        Dictionary of merchant -> category_id
    """
    return {
        merchant: category_id
        for (ws_id, merchant), category_id in _MERCHANT_CATEGORY_MAP.items()
        if ws_id == workspace_id
    }
