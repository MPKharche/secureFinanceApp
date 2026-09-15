"""Idempotency key generation and duplicate detection."""
import hashlib
import time
import logging
from typing import Optional

from database import db
from config import config

logger = logging.getLogger(__name__)

def generate_idempotency_key(
    message_text: str,
    user_id: str,
    telegram_message_id: Optional[str] = None
) -> str:
    """
    Generate idempotency key for duplicate detection.
    
    Groups messages within 5-minute windows. Same message text from same user
    within the window = same key.
    
    Args:
        message_text: The transaction message text
        user_id: User ID
        telegram_message_id: Optional Telegram message ID for uniqueness
        
    Returns:
        SHA256 hash as idempotency key
    """
    # Time bucket: 5-minute windows
    time_bucket = int(time.time() / config.IDEMPOTENCY_WINDOW_SECONDS)
    
    # Normalize message text
    normalized_text = message_text.strip().lower()
    
    # Create hash input
    if telegram_message_id:
        # Prefer telegram message ID for uniqueness
        raw = f"{user_id}:{telegram_message_id}"
    else:
        # Fall back to text + time bucket
        raw = f"{user_id}:{normalized_text}:{time_bucket}"
    
    # Generate SHA256 hash
    key = hashlib.sha256(raw.encode()).hexdigest()
    
    return key

async def is_duplicate(idempotency_key: str) -> bool:
    """
    Check if idempotency key already exists.
    
    Searches mcp_call_log for the key within the last hour.
    
    Args:
        idempotency_key: The key to check
        
    Returns:
        True if duplicate, False if unique
    """
    result = await db.fetchval(
        """
        SELECT 1 FROM mcp_call_log 
        WHERE idempotency_key = $1 
        AND called_at > NOW() - INTERVAL '1 hour'
        LIMIT 1
        """,
        idempotency_key
    )
    
    if result:
        logger.info(f"Duplicate detected: {idempotency_key}")
        return True
    
    return False

async def get_cached_response(idempotency_key: str) -> Optional[dict]:
    """
    Get cached response for duplicate request.
    
    Args:
        idempotency_key: The key to lookup
        
    Returns:
        Response dict if found, None otherwise
    """
    row = await db.fetchrow(
        """
        SELECT response FROM mcp_call_log 
        WHERE idempotency_key = $1 
        AND success = true
        AND called_at > NOW() - INTERVAL '1 hour'
        ORDER BY called_at DESC
        LIMIT 1
        """,
        idempotency_key
    )
    
    if row and row['response']:
        logger.info(f"Returning cached response for: {idempotency_key}")
        return row['response']
    
    return None
