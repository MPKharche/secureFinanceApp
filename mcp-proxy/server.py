"""Main MCP Proxy Server."""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import httpx

from config import config
from database import db
from models import MCPRequest, MCPResponse, CheckpointRequest
from idempotency import generate_idempotency_key, is_duplicate, get_cached_response
from circuit_breaker import circuit_breaker
from wal import append_to_wal, rotate_old_wal_files, get_wal_size_mb
from telegram_alerter import alerter
from checkpoint_handler import save_checkpoint, recover_unprocessed_checkpoints
from retry_worker import retry_worker
from metrics import (
    mcp_calls_total, call_duration_seconds, 
    update_metrics, get_metrics_content
)

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting MCP Proxy Server...")
    config.validate()
    
    await db.connect()
    await recover_unprocessed_checkpoints()
    await retry_worker.start()
    
    # Start background tasks
    asyncio.create_task(periodic_wal_rotation())
    asyncio.create_task(periodic_metrics_update())
    
    logger.info(f"MCP Proxy Server running on {config.HOST}:{config.MCP_PROXY_PORT}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MCP Proxy Server...")
    await retry_worker.stop()
    await db.close()

# Create FastAPI app
app = FastAPI(
    title="MCP Proxy Server",
    description="Sync reliability proxy for Telegram-Securo transactions",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/mcp")
async def proxy_mcp_call(request: Request) -> JSONResponse:
    """
    Proxy MCP calls from Hermes to Securo MCP.
    
    Injects apply=true for propose_* tools, handles retries, logs everything.
    """
    start_time = time.time()
    
    try:
        # Parse request body
        body = await request.json()
        mcp_request = MCPRequest(**body)
        
        # Extract context (would parse from request headers)
        user_id = "default_user"  # TODO: Extract from auth
        telegram_message_id = None  # TODO: Extract from request
        
        # Generate idempotency key
        params_str = str(mcp_request.params)
        idem_key = generate_idempotency_key(params_str, user_id, telegram_message_id)
        
        # Check if duplicate
        if await is_duplicate(idem_key):
            logger.info(f"Duplicate request detected: {idem_key}")
            cached_response = await get_cached_response(idem_key)
            if cached_response:
                return JSONResponse(cached_response)
        
        # Inject apply=true for propose_* tools
        params_modified = False
        tool_name = mcp_request.params.get('name', '')
        
        if tool_name.startswith('propose_'):
            arguments = mcp_request.params.get('arguments', {})
            if 'apply' not in arguments or not arguments['apply']:
                arguments['apply'] = True
                mcp_request.params['arguments'] = arguments
                params_modified = True
                logger.info(f"Injected apply=true for {tool_name}")
        
        # Check circuit breaker
        if not circuit_breaker.should_attempt():
            logger.warning("Circuit breaker open, queueing request")
            await queue_for_retry(mcp_request, idem_key, user_id)
            raise HTTPException(
                status_code=503,
                detail="Backend unavailable, request queued for retry"
            )
        
        # Write to WAL
        await append_to_wal(mcp_request.dict(), idem_key)
        
        # Log call start
        call_log_id = await log_mcp_call_start(
            mcp_request, idem_key, params_modified, user_id
        )
        
        # Forward to Securo MCP
        try:
            response = await forward_to_securo_mcp(mcp_request)
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log success
            await log_mcp_call_end(call_log_id, True, response, duration_ms)
            circuit_breaker.record_success()
            mcp_calls_total.labels(tool=tool_name, status='success').inc()
            call_duration_seconds.observe(duration_ms / 1000)
            
            return JSONResponse(response)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log failure
            await log_mcp_call_end(call_log_id, False, None, duration_ms, str(e))
            circuit_breaker.record_failure()
            mcp_calls_total.labels(tool=tool_name, status='failure').inc()
            
            # Queue for retry
            await queue_for_retry(mcp_request, idem_key, user_id, str(e))
            
            raise HTTPException(status_code=502, detail=f"MCP call failed: {e}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing MCP request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/checkpoint")
async def save_hermes_checkpoint(checkpoint: CheckpointRequest) -> JSONResponse:
    """Save Hermes checkpoint for crash recovery."""
    try:
        result = await save_checkpoint(checkpoint)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Error saving checkpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint with system stats."""
    try:
        await update_metrics()
        
        # Gather stats
        pending_count = await db.fetchval(
            "SELECT COUNT(*) FROM pending_transactions WHERE status IN ('pending', 'retrying')"
        )
        
        failed_last_hour = await db.fetchval(
            """
            SELECT COUNT(*) FROM mcp_call_log 
            WHERE success = false 
            AND called_at > NOW() - INTERVAL '1 hour'
            """
        )
        
        calls_last_hour = await db.fetchval(
            "SELECT COUNT(*) FROM mcp_call_log WHERE called_at > NOW() - INTERVAL '1 hour'"
        )
        
        success_rate = 100.0 if calls_last_hour == 0 else \
            ((calls_last_hour - failed_last_hour) / calls_last_hour * 100)
        
        return JSONResponse({
            "status": "healthy",
            "pending_transactions": pending_count or 0,
            "failed_transactions_last_hour": failed_last_hour or 0,
            "mcp_calls_last_hour": calls_last_hour or 0,
            "success_rate": round(success_rate, 1),
            "retry_worker_running": retry_worker.running,
            "circuit_breaker_state": circuit_breaker.get_state(),
            "wal_size_mb": round(get_wal_size_mb(), 2)
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse({"status": "unhealthy", "error": str(e)}, status_code=500)

@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    await update_metrics()
    content, content_type = get_metrics_content()
    return Response(content=content, media_type=content_type)

# Helper functions

async def forward_to_securo_mcp(mcp_request: MCPRequest) -> dict:
    """Forward MCP request to Securo MCP server."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            config.SECURO_MCP_URL,
            json=mcp_request.dict(),
            headers={
                "Authorization": f"Bearer {config.SECURO_MCP_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()

async def log_mcp_call_start(
    mcp_request: MCPRequest,
    idem_key: str,
    params_modified: bool,
    user_id: str
) -> str:
    """Log MCP call start to mcp_call_log table."""
    row = await db.fetchrow(
        """
        INSERT INTO mcp_call_log 
        (tool_name, params, params_modified, source, idempotency_key, success)
        VALUES ($1, $2, $3, $4, $5, false)
        RETURNING id
        """,
        mcp_request.params.get('name', 'unknown'),
        mcp_request.params,
        params_modified,
        'hermes',
        idem_key
    )
    return row['id']

async def log_mcp_call_end(
    call_log_id: str,
    success: bool,
    response: Optional[dict] = None,
    duration_ms: Optional[int] = None,
    error: Optional[str] = None
):
    """Update MCP call log with result."""
    await db.execute(
        """
        UPDATE mcp_call_log 
        SET success = $1, response = $2, duration_ms = $3, error_message = $4
        WHERE id = $5
        """,
        success, response, duration_ms, error, call_log_id
    )

async def queue_for_retry(
    mcp_request: MCPRequest,
    idem_key: str,
    user_id: str,
    error: Optional[str] = None
):
    """Add failed MCP call to retry queue."""
    retry_at = datetime.utcnow() + timedelta(seconds=config.RETRY_INTERVAL_1)
    
    await db.execute(
        """
        INSERT INTO pending_transactions 
        (workspace_id, user_id, raw_message, mcp_tool_name, mcp_params, 
         idempotency_key, retry_at, last_error, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending')
        """,
        None,  # TODO: Extract workspace_id
        user_id,
        str(mcp_request.params),
        mcp_request.params.get('name', 'unknown'),
        mcp_request.params.get('arguments', {}),
        idem_key,
        retry_at,
        error
    )
    logger.info(f"Queued for retry: {idem_key}")

# Background tasks

async def periodic_wal_rotation():
    """Rotate WAL files daily."""
    while True:
        try:
            await asyncio.sleep(86400)  # 24 hours
            await rotate_old_wal_files()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in WAL rotation: {e}")

async def periodic_metrics_update():
    """Update metrics every 30 seconds."""
    while True:
        try:
            await asyncio.sleep(30)
            await update_metrics()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=config.HOST,
        port=config.MCP_PROXY_PORT,
        log_level=config.LOG_LEVEL.lower()
    )
