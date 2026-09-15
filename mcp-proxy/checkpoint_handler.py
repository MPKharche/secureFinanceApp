"""Hermes checkpoint save/recovery API."""
import logging
from typing import Dict, Any

from database import db
from models import CheckpointRequest

logger = logging.getLogger(__name__)


async def save_checkpoint(checkpoint: CheckpointRequest) -> dict:
    """
    Save Hermes checkpoint to database.
    
    Upserts on (session_id, telegram_chat_id) to keep only latest checkpoint.
    
    Args:
        checkpoint: Checkpoint data from Hermes
        
    Returns:
        {"status": "saved"}
    """
    await db.execute(
        """
        INSERT INTO hermes_checkpoints 
            (session_id, telegram_chat_id, conversation_state, pending_mcp_call, processed)
        VALUES ($1, $2, $3, $4, false)
        ON CONFLICT (session_id, telegram_chat_id) 
        DO UPDATE SET 
            conversation_state = EXCLUDED.conversation_state,
            pending_mcp_call = EXCLUDED.pending_mcp_call,
            created_at = NOW(),
            processed = false
        """,
        checkpoint.session_id,
        checkpoint.telegram_chat_id,
        checkpoint.conversation_state,
        checkpoint.pending_mcp_call
    )
    
    logger.info(f"Saved checkpoint for session {checkpoint.session_id}")
    return {"status": "saved"}


async def recover_unprocessed_checkpoints() -> int:
    """
    Recover unprocessed checkpoints after restart.
    
    Checks if pending MCP calls were completed. If not, adds to retry queue.
    Marks all checkpoints as processed.
    
    Returns:
        Number of checkpoints recovered
    """
    checkpoints = await db.fetch(
        "SELECT * FROM hermes_checkpoints WHERE processed = false"
    )
    
    recovered_count = 0
    
    for row in checkpoints:
        checkpoint_id = row['id']
        pending_call = row['pending_mcp_call']
        
        if pending_call:
            # Check if transaction was completed
            tool_name = pending_call.get('tool')
            params = pending_call.get('params', {})
            
            # Look for matching transaction in last hour
            tx_exists = await check_transaction_exists(params)
            
            if not tx_exists:
                # Add to retry queue
                await add_to_retry_queue_from_checkpoint(row)
                recovered_count += 1
                logger.warning(
                    f"Recovered unprocessed checkpoint {checkpoint_id}, "
                    f"added to retry queue"
                )
        
        # Mark as processed
        await db.execute(
            "UPDATE hermes_checkpoints SET processed = true WHERE id = $1",
            checkpoint_id
        )
    
    if recovered_count > 0:
        logger.info(f"Recovered {recovered_count} unprocessed checkpoints")
    
    return recovered_count


async def check_transaction_exists(params: dict) -> bool:
    """
    Check if transaction matching params exists in database.
    
    Args:
        params: MCP call params
        
    Returns:
        True if transaction exists
    """
    description = params.get('description')
    amount = params.get('amount')
    date = params.get('date')
    
    if not (description and amount):
        return False
    
    result = await db.fetchval(
        """
        SELECT 1 FROM transactions 
        WHERE description = $1 
        AND amount = $2 
        AND date = $3
        AND created_at > NOW() - INTERVAL '1 hour'
        LIMIT 1
        """,
        description, amount, date
    )
    
    return result is not None


async def add_to_retry_queue_from_checkpoint(checkpoint_row: Dict[str, Any]) -> None:
    """
    Add checkpoint's pending call to retry queue.
    
    Args:
        checkpoint_row: Checkpoint database row
    """
    pending_call = checkpoint_row['pending_mcp_call']
    
    # Extract workspace and user from conversation state
    conv_state = checkpoint_row['conversation_state']
    
    # Parse workspace_id and user_id from conversation state
    # ponytail: simplified extraction - real impl would parse Hermes state structure
    workspace_id = conv_state.get('workspace_id')
    user_id = conv_state.get('user_id')
    
    await db.execute(
        """
        INSERT INTO pending_transactions 
            (workspace_id, user_id, telegram_chat_id, raw_message, 
             mcp_tool_name, mcp_params, retry_at, status)
        VALUES ($1, $2, $3, $4, $5, $6, NOW(), 'pending')
        """,
        workspace_id,
        user_id,
        checkpoint_row['telegram_chat_id'],
        "Recovered from checkpoint",
        pending_call.get('tool'),
        pending_call.get('params')
    )
    
    logger.info(
        f"Added checkpoint {checkpoint_row['id']} to retry queue: "
        f"{pending_call.get('tool')}"
    )
