"""Background retry worker for failed MCP calls."""
import asyncio
import logging
import httpx
from datetime import datetime, timedelta
from typing import List

from database import db
from config import config
from models import PendingTransaction
from circuit_breaker import circuit_breaker
from telegram_alerter import alerter
from metrics import mcp_calls_total

logger = logging.getLogger(__name__)

class RetryWorker:
    """Background worker that retries failed MCP calls."""
    
    def __init__(self):
        self.running = False
        self.task = None
    
    async def start(self):
        """Start the retry worker loop."""
        self.running = True
        self.task = asyncio.create_task(self._worker_loop())
        logger.info("Retry worker started")
    
    async def stop(self):
        """Stop the retry worker loop."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Retry worker stopped")
    
    async def _worker_loop(self):
        """Main worker loop."""
        while self.running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                await self._process_pending_transactions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in retry worker loop: {e}", exc_info=True)
    
    async def _process_pending_transactions(self):
        """Fetch and process pending transactions."""
        # Fetch transactions due for retry
        rows = await db.fetch(
            """
            SELECT * FROM pending_transactions 
            WHERE status IN ('pending', 'retrying')
            AND retry_at <= NOW()
            ORDER BY retry_at
            LIMIT 100
            """
        )
        
        if not rows:
            return
        
        logger.info(f"Processing {len(rows)} pending transactions")
        
        for row in rows:
            await self._retry_transaction(row)
    
    async def _retry_transaction(self, row: dict):
        """
        Retry a single pending transaction.
        
        Args:
            row: Database row from pending_transactions
        """
        pending_id = row['id']
        attempt_count = row['attempt_count']
        max_attempts = row['max_attempts']
        
        # Increment attempt count
        new_attempt_count = attempt_count + 1
        await db.execute(
            """
            UPDATE pending_transactions 
            SET attempt_count = $1, status = 'retrying'
            WHERE id = $2
            """,
            new_attempt_count, pending_id
        )
        
        logger.info(
            f"Retrying pending_tx {pending_id}, attempt {new_attempt_count}/{max_attempts}"
        )
        
        # Check circuit breaker
        if not circuit_breaker.should_attempt():
            logger.warning(f"Circuit breaker open, skipping retry of {pending_id}")
            # Reschedule for later
            await self._reschedule_retry(pending_id, new_attempt_count, max_attempts)
            return
        
        # Attempt MCP call
        try:
            result = await self._call_securo_mcp(row)
            
            # Success
            await self._handle_success(pending_id, result)
            circuit_breaker.record_success()
            mcp_calls_total.labels(tool=row['mcp_tool_name'], status='success').inc()
            
        except Exception as e:
            # Failure
            await self._handle_failure(pending_id, new_attempt_count, max_attempts, str(e))
            circuit_breaker.record_failure()
            mcp_calls_total.labels(tool=row['mcp_tool_name'], status='failure').inc()
    
    async def _call_securo_mcp(self, row: dict) -> dict:
        """
        Call Securo MCP with the pending transaction params.
        
        Args:
            row: Pending transaction row
            
        Returns:
            MCP response dict
            
        Raises:
            Exception on failure
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                config.SECURO_MCP_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": row['mcp_tool_name'],
                        "arguments": row['mcp_params']
                    }
                },
                headers={
                    "Authorization": f"Bearer {config.SECURO_MCP_TOKEN}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            
            response.raise_for_status()
            return response.json()
    
    async def _handle_success(self, pending_id, result: dict):
        """Mark transaction as successful."""
        await db.execute(
            """
            UPDATE pending_transactions 
            SET status = 'success', completed_at = NOW()
            WHERE id = $1
            """,
            pending_id
        )
        logger.info(f"Successfully retried pending_tx {pending_id}")
    
    async def _handle_failure(
        self, 
        pending_id, 
        attempt_count: int, 
        max_attempts: int, 
        error: str
    ):
        """Handle failed retry attempt."""
        if attempt_count >= max_attempts:
            # Final failure
            await db.execute(
                """
                UPDATE pending_transactions 
                SET status = 'failed', 
                    completed_at = NOW(),
                    last_error = $1
                WHERE id = $2
                """,
                error, pending_id
            )
            
            logger.error(
                f"Failed to retry pending_tx {pending_id} after {attempt_count} attempts"
            )
            
            # Send Telegram alert
            row = await db.fetchrow(
                "SELECT * FROM pending_transactions WHERE id = $1",
                pending_id
            )
            if row:
                from models import PendingTransaction
                pending_tx = PendingTransaction(**dict(row))
                await alerter.send_failure_alert(pending_tx)
        
        else:
            # Schedule next retry
            await self._reschedule_retry(pending_id, attempt_count, max_attempts)
    
    async def _reschedule_retry(
        self, 
        pending_id, 
        attempt_count: int, 
        max_attempts: int
    ):
        """Schedule next retry attempt."""
        # Retry intervals: 15s, then 30s
        if attempt_count == 1:
            delay = config.RETRY_INTERVAL_1
        else:
            delay = config.RETRY_INTERVAL_2
        
        retry_at = datetime.utcnow() + timedelta(seconds=delay)
        
        await db.execute(
            """
            UPDATE pending_transactions 
            SET retry_at = $1, status = 'pending'
            WHERE id = $2
            """,
            retry_at, pending_id
        )
        
        logger.info(f"Scheduled retry for pending_tx {pending_id} in {delay}s")

# Global retry worker instance
retry_worker = RetryWorker()
