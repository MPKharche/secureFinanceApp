"""Category learning service for merchant mappings."""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.merchant_mapping import MerchantMapping


def normalize_merchant_name(merchant: str) -> str:
    """
    Normalize merchant name for consistent matching.
    
    - Lowercase
    - Remove special characters
    - Remove extra whitespace
    - Common abbreviations (Pvt Ltd, Private Limited, etc.)
    
    Args:
        merchant: Raw merchant name
        
    Returns:
        Normalized merchant name
    """
    if not merchant:
        return ""
    
    # Lowercase
    normalized = merchant.lower()
    
    # Remove common suffixes
    suffixes = [
        r'\s+pvt\.?\s+ltd\.?',
        r'\s+private\s+limited',
        r'\s+ltd\.?',
        r'\s+inc\.?',
        r'\s+llc\.?',
        r'\s+corporation',
        r'\s+corp\.?',
    ]
    for suffix in suffixes:
        normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)
    
    # Remove special characters except spaces and hyphens
    normalized = re.sub(r'[^a-z0-9\s\-]', '', normalized)
    
    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized


async def get_category_for_merchant(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    merchant: str,
) -> Optional[uuid.UUID]:
    """
    Look up category for a merchant based on learned mappings.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        merchant: Merchant name (will be normalized)
        
    Returns:
        Category ID if mapping exists, None otherwise
    """
    normalized = normalize_merchant_name(merchant)
    
    if not normalized:
        return None
    
    query = select(MerchantMapping).where(
        and_(
            MerchantMapping.workspace_id == workspace_id,
            MerchantMapping.merchant_name_normalized == normalized,
        )
    )
    
    result = await db.execute(query)
    mapping = result.scalar_one_or_none()
    
    if mapping:
        # Update usage stats
        await db.execute(
            update(MerchantMapping)
            .where(MerchantMapping.id == mapping.id)
            .values(
                transaction_count=MerchantMapping.transaction_count + 1,
                last_used_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        
        return mapping.category_id
    
    return None


async def learn_merchant_category(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    merchant: str,
    category_id: uuid.UUID,
) -> MerchantMapping:
    """
    Create or update merchant-category mapping.
    
    If mapping exists, updates the category and increments usage count.
    If new, creates a new mapping.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        merchant: Merchant name (will be normalized)
        category_id: Category ID to map to
        
    Returns:
        MerchantMapping instance
    """
    normalized = normalize_merchant_name(merchant)
    
    # Check if mapping exists
    query = select(MerchantMapping).where(
        and_(
            MerchantMapping.workspace_id == workspace_id,
            MerchantMapping.merchant_name_normalized == normalized,
        )
    )
    result = await db.execute(query)
    mapping = result.scalar_one_or_none()
    
    now = datetime.now(timezone.utc)
    
    if mapping:
        # Update existing mapping
        mapping.category_id = category_id
        mapping.transaction_count += 1
        mapping.last_used_at = now
    else:
        # Create new mapping
        mapping = MerchantMapping(
            workspace_id=workspace_id,
            merchant_name_normalized=normalized,
            category_id=category_id,
            transaction_count=1,
            last_used_at=now,
        )
        db.add(mapping)
    
    await db.commit()
    await db.refresh(mapping)
    
    return mapping
