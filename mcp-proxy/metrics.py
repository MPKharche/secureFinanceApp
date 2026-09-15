"""Prometheus metrics for monitoring."""
import logging
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

from database import db
from wal import get_wal_size_mb
from circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)

# Define metrics
mcp_calls_total = Counter(
    'mcp_proxy_calls_total',
    'Total MCP calls',
    ['tool', 'status']  # Labels: tool name, success/failure
)

retry_queue_size = Gauge(
    'mcp_proxy_retry_queue_size',
    'Number of pending transactions'
)

call_duration_seconds = Histogram(
    'mcp_proxy_call_duration_seconds',
    'MCP call duration',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

sync_lag_seconds = Gauge(
    'telegram_sync_lag_seconds',
    'Time from Telegram message to DB save'
)

circuit_breaker_state_gauge = Gauge(
    'mcp_proxy_circuit_breaker_state',
    'Circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)'
)

wal_size_mb_gauge = Gauge(
    'mcp_proxy_wal_size_mb',
    'Write-ahead log size in MB'
)

async def update_metrics():
    """Update gauge metrics from database."""
    try:
        # Pending transaction count
        count = await db.fetchval(
            "SELECT COUNT(*) FROM pending_transactions WHERE status IN ('pending', 'retrying')"
        )
        retry_queue_size.set(count or 0)
        
        # WAL size
        wal_size = get_wal_size_mb()
        wal_size_mb_gauge.set(wal_size)
        
        # Circuit breaker state
        cb_state = circuit_breaker.get_state()
        state_value = {"CLOSED": 0, "OPEN": 1, "HALF_OPEN": 2}.get(cb_state, 0)
        circuit_breaker_state_gauge.set(state_value)
        
    except Exception as e:
        logger.error(f"Failed to update metrics: {e}")

def get_metrics_content() -> tuple:
    """
    Get Prometheus metrics in text format.
    
    Returns:
        (content, content_type) tuple
    """
    return generate_latest(), CONTENT_TYPE_LATEST
