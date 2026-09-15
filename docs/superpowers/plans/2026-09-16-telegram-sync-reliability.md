# Telegram-Securo Sync Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an MCP proxy server that guarantees 100% sync reliability between Telegram transactions and Securo database through automatic parameter injection, persistent retry queue, and crash recovery.

**Architecture:** FastAPI proxy server sits between Hermes and Securo MCP, intercepts all calls to inject `apply=true`, implements retry worker with circuit breaker, provides checkpoint API for crash recovery, exports Prometheus metrics, and sends Telegram alerts on failures.

**Tech Stack:** Python 3.11+, FastAPI, asyncpg, python-telegram-bot, prometheus-client, PostgreSQL 16

**Spec:** `/root/system/docs/2026-09-16-telegram-sync-reliability-design.md`

## Global Constraints

- Python 3.11+ required (asyncio features)
- PostgreSQL 16+ (gen_random_uuid support)
- No external queue services (Redis/RabbitMQ) - use PostgreSQL for queue
- All secrets in `.env` file, never committed
- Resource limits: 256MB RAM, 50% CPU
- All times in UTC internally, convert to IST for display
- Retry intervals: 15s (attempt 1), 30s (attempt 2)
- Max 2 retry attempts before alerting
- Idempotency window: 5 minutes
- WAL retention: 7 days
- Circuit breaker threshold: 5 consecutive failures
- Circuit breaker recovery timeout: 60 seconds

---

## File Structure

```
/root/apps/secureFinanceApp/
├── mcp-proxy/
│   ├── server.py                    # Main FastAPI proxy server
│   ├── retry_worker.py              # Background retry loop
│   ├── circuit_breaker.py           # Circuit breaker implementation
│   ├── idempotency.py               # Duplicate detection
│   ├── wal.py                       # Write-ahead log
│   ├── telegram_alerter.py          # Send Telegram alerts
│   ├── checkpoint_handler.py        # Checkpoint save/recovery API
│   ├── metrics.py                   # Prometheus metrics
│   ├── database.py                  # Database connection pool
│   ├── config.py                    # Configuration management
│   ├── models.py                    # Data models
│   ├── requirements.txt             # Python dependencies
│   ├── .env.example                 # Example environment variables
│   ├── README.md                    # Setup and usage docs
│   ├── systemd/
│   │   └── mcp-proxy.service        # Systemd service file
│   ├── migrations/
│   │   └── 001_add_sync_tables.sql  # Database migrations
│   └── wal/                         # Write-ahead log directory
│       └── .gitkeep
└── backend/
    └── alembic/
        └── versions/
            └── 078_mcp_sync_tables.py  # Alembic migration for sync tables
```

---

### Task 1: Database Schema and Migrations

**Files:**
- Create: `/root/apps/secureFinanceApp/mcp-proxy/migrations/001_add_sync_tables.sql`
- Create: `/root/apps/secureFinanceApp/backend/alembic/versions/078_mcp_sync_tables.py`

**Interfaces:**
- Produces: Tables `pending_transactions`, `mcp_call_log`, `hermes_checkpoints`

- [ ] **Step 1: Write SQL migration for pending_transactions table**

```sql
-- /root/apps/secureFinanceApp/mcp-proxy/migrations/001_add_sync_tables.sql

-- Pending transactions retry queue
CREATE TABLE IF NOT EXISTS pending_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Source data
    telegram_message_id TEXT,
    telegram_chat_id TEXT,
    raw_message TEXT NOT NULL,
    
    -- MCP call details
    mcp_tool_name TEXT NOT NULL,
    mcp_params JSONB NOT NULL,
    
    -- Idempotency
    idempotency_key TEXT UNIQUE,
    
    -- Retry tracking
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 2,
    last_error TEXT,
    last_error_code TEXT,
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    retry_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Status: pending, retrying, success, failed
    status TEXT NOT NULL DEFAULT 'pending',
    CONSTRAINT valid_status CHECK (status IN ('pending', 'retrying', 'success', 'failed'))
);

CREATE INDEX idx_pending_tx_retry ON pending_transactions(retry_at) 
    WHERE status IN ('pending', 'retrying');
CREATE INDEX idx_pending_tx_status ON pending_transactions(status);
CREATE INDEX idx_pending_tx_telegram ON pending_transactions(telegram_message_id);
CREATE INDEX idx_pending_tx_idempotency ON pending_transactions(idempotency_key);
CREATE INDEX idx_pending_tx_user ON pending_transactions(user_id);
```

- [ ] **Step 2: Add mcp_call_log audit table**

Append to `/root/apps/secureFinanceApp/mcp-proxy/migrations/001_add_sync_tables.sql`:

```sql
-- MCP call audit log
CREATE TABLE IF NOT EXISTS mcp_call_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Call details
    tool_name TEXT NOT NULL,
    params JSONB NOT NULL,
    params_modified BOOLEAN NOT NULL DEFAULT false,
    
    -- Context
    source TEXT NOT NULL,  -- 'hermes', 'web', 'api', 'retry_worker'
    workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    telegram_message_id TEXT,
    idempotency_key TEXT,
    
    -- Result
    success BOOLEAN NOT NULL,
    response JSONB,
    error_message TEXT,
    error_code TEXT,
    duration_ms INTEGER,
    
    -- Timing
    called_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Linking
    pending_transaction_id UUID REFERENCES pending_transactions(id) ON DELETE SET NULL,
    created_transaction_id UUID REFERENCES transactions(id) ON DELETE SET NULL
);

CREATE INDEX idx_mcp_log_time ON mcp_call_log(called_at);
CREATE INDEX idx_mcp_log_success ON mcp_call_log(success);
CREATE INDEX idx_mcp_log_tool ON mcp_call_log(tool_name);
CREATE INDEX idx_mcp_log_telegram ON mcp_call_log(telegram_message_id);
CREATE INDEX idx_mcp_log_idempotency ON mcp_call_log(idempotency_key);
```

- [ ] **Step 3: Add hermes_checkpoints table**

Append to `/root/apps/secureFinanceApp/mcp-proxy/migrations/001_add_sync_tables.sql`:

```sql
-- Hermes crash recovery checkpoints
CREATE TABLE IF NOT EXISTS hermes_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Session identification
    session_id TEXT NOT NULL,
    telegram_chat_id TEXT NOT NULL,
    
    -- State snapshot
    conversation_state JSONB NOT NULL,
    pending_mcp_call JSONB,
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    processed BOOLEAN NOT NULL DEFAULT false,
    
    -- Only keep latest checkpoint per session
    UNIQUE(session_id, telegram_chat_id)
);

CREATE INDEX idx_checkpoint_unprocessed ON hermes_checkpoints(processed) 
    WHERE processed = false;
```

- [ ] **Step 4: Test SQL migration**

Run:
```bash
docker exec securo-db-1 psql -U postgres -d securo < /root/apps/secureFinanceApp/mcp-proxy/migrations/001_add_sync_tables.sql
```

Expected: All tables created successfully

- [ ] **Step 5: Verify tables exist**

Run:
```bash
docker exec securo-db-1 psql -U postgres -d securo -c "\dt pending_transactions mcp_call_log hermes_checkpoints"
```

Expected: Shows all 3 tables

- [ ] **Step 6: Create Alembic migration wrapper**

```python
# /root/apps/secureFinanceApp/backend/alembic/versions/078_mcp_sync_tables.py
"""add mcp sync tables

Revision ID: 078_mcp_sync_tables
Revises: 077_previous_migration
Create Date: 2026-09-16 00:56:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '078_mcp_sync_tables'
down_revision = '077_previous_migration'  # Update with actual previous revision
branch_labels = None
depends_on = None

def upgrade():
    # Read and execute SQL from migrations directory
    import pathlib
    sql_file = pathlib.Path(__file__).parent.parent.parent.parent / 'mcp-proxy' / 'migrations' / '001_add_sync_tables.sql'
    with open(sql_file) as f:
        op.execute(f.read())

def downgrade():
    op.execute('DROP TABLE IF EXISTS hermes_checkpoints CASCADE')
    op.execute('DROP TABLE IF EXISTS mcp_call_log CASCADE')
    op.execute('DROP TABLE IF EXISTS pending_transactions CASCADE')
```

- [ ] **Step 7: Commit**

```bash
git add mcp-proxy/migrations/001_add_sync_tables.sql backend/alembic/versions/078_mcp_sync_tables.py
git commit -m "feat(mcp-proxy): add database schema for sync reliability

- pending_transactions table for retry queue
- mcp_call_log table for audit trail
- hermes_checkpoints table for crash recovery
- All tables with appropriate indexes"
```

---

### Task 2: Configuration and Models

**Files:**
- Create: `/root/apps/secureFinanceApp/mcp-proxy/config.py`
- Create: `/root/apps/secureFinanceApp/mcp-proxy/models.py`
- Create: `/root/apps/secureFinanceApp/mcp-proxy/.env.example`
- Create: `/root/apps/secureFinanceApp/mcp-proxy/requirements.txt`

**Interfaces:**
- Produces: `Config` class with all settings, Pydantic models for database records

- [ ] **Step 1: Write configuration management**

```python
# /root/apps/secureFinanceApp/mcp-proxy/config.py
"""Configuration management for MCP Proxy."""
import os
from pathlib import Path
from typing import Optional

class Config:
    """MCP Proxy configuration from environment variables."""
    
    # Server
    MCP_PROXY_PORT: int = int(os.getenv('MCP_PROXY_PORT', '8766'))
    HOST: str = os.getenv('HOST', '127.0.0.1')
    
    # Securo MCP
    SECURO_MCP_URL: str = os.getenv('SECURO_MCP_URL', 'http://127.0.0.1:8765/mcp')
    SECURO_MCP_TOKEN: str = os.getenv('SECURO_MCP_TOKEN', '')
    
    # Database
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:15432/securo')
    DATABASE_POOL_MIN: int = int(os.getenv('DATABASE_POOL_MIN', '2'))
    DATABASE_POOL_MAX: int = int(os.getenv('DATABASE_POOL_MAX', '10'))
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_ALERT_CHAT_ID: str = os.getenv('TELEGRAM_ALERT_CHAT_ID', '')
    
    # Retry
    RETRY_INTERVAL_1: int = int(os.getenv('RETRY_INTERVAL_1', '15'))
    RETRY_INTERVAL_2: int = int(os.getenv('RETRY_INTERVAL_2', '30'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '2'))
    
    # Circuit Breaker
    CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv('CIRCUIT_BREAKER_THRESHOLD', '5'))
    CIRCUIT_BREAKER_TIMEOUT: int = int(os.getenv('CIRCUIT_BREAKER_TIMEOUT', '60'))
    
    # Write-Ahead Log
    WAL_DIR: Path = Path(os.getenv('WAL_DIR', '/root/apps/secureFinanceApp/mcp-proxy/wal'))
    WAL_RETENTION_DAYS: int = int(os.getenv('WAL_RETENTION_DAYS', '7'))
    
    # Idempotency
    IDEMPOTENCY_WINDOW_SECONDS: int = int(os.getenv('IDEMPOTENCY_WINDOW_SECONDS', '300'))
    
    # Monitoring
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        errors = []
        
        if not cls.SECURO_MCP_TOKEN:
            errors.append('SECURO_MCP_TOKEN is required')
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append('TELEGRAM_BOT_TOKEN is required')
        if not cls.TELEGRAM_ALERT_CHAT_ID:
            errors.append('TELEGRAM_ALERT_CHAT_ID is required')
            
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        # Ensure WAL directory exists
        cls.WAL_DIR.mkdir(parents=True, exist_ok=True)

config = Config()
```

- [ ] **Step 2: Write data models**

```python
# /root/apps/secureFinanceApp/mcp-proxy/models.py
"""Pydantic models for MCP Proxy."""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID

class PendingTransaction(BaseModel):
    """Pending transaction in retry queue."""
    id: UUID
    workspace_id: UUID
    user_id: UUID
    telegram_message_id: Optional[str]
    telegram_chat_id: Optional[str]
    raw_message: str
    mcp_tool_name: str
    mcp_params: Dict[str, Any]
    idempotency_key: Optional[str]
    attempt_count: int = 0
    max_attempts: int = 2
    last_error: Optional[str]
    last_error_code: Optional[str]
    created_at: datetime
    retry_at: datetime
    completed_at: Optional[datetime]
    status: str  # pending, retrying, success, failed

class MCPCallLog(BaseModel):
    """MCP call audit log entry."""
    id: UUID
    tool_name: str
    params: Dict[str, Any]
    params_modified: bool
    source: str
    workspace_id: Optional[UUID]
    user_id: Optional[UUID]
    telegram_message_id: Optional[str]
    idempotency_key: Optional[str]
    success: bool
    response: Optional[Dict[str, Any]]
    error_message: Optional[str]
    error_code: Optional[str]
    duration_ms: Optional[int]
    called_at: datetime
    pending_transaction_id: Optional[UUID]
    created_transaction_id: Optional[UUID]

class HermesCheckpoint(BaseModel):
    """Hermes crash recovery checkpoint."""
    id: UUID
    session_id: str
    telegram_chat_id: str
    conversation_state: Dict[str, Any]
    pending_mcp_call: Optional[Dict[str, Any]]
    created_at: datetime
    processed: bool

class MCPRequest(BaseModel):
    """MCP JSON-RPC request."""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)

class MCPResponse(BaseModel):
    """MCP JSON-RPC response."""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

class CheckpointRequest(BaseModel):
    """Checkpoint save request from Hermes."""
    session_id: str
    telegram_chat_id: str
    conversation_state: Dict[str, Any]
    pending_mcp_call: Optional[Dict[str, Any]] = None
```

- [ ] **Step 3: Create .env.example**

```bash
# /root/apps/secureFinanceApp/mcp-proxy/.env.example
# MCP Proxy Configuration

# Server
MCP_PROXY_PORT=8766
HOST=127.0.0.1

# Securo MCP
SECURO_MCP_URL=http://127.0.0.1:8765/mcp
SECURO_MCP_TOKEN=your_mcp_token_here

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:15432/securo
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=10

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALERT_CHAT_ID=your_chat_id_here

# Retry
RETRY_INTERVAL_1=15
RETRY_INTERVAL_2=30
MAX_RETRIES=2

# Circuit Breaker
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60

# Write-Ahead Log
WAL_DIR=/root/apps/secureFinanceApp/mcp-proxy/wal
WAL_RETENTION_DAYS=7

# Idempotency
IDEMPOTENCY_WINDOW_SECONDS=300

# Monitoring
LOG_LEVEL=INFO
```

- [ ] **Step 4: Create requirements.txt**

```
# /root/apps/secureFinanceApp/mcp-proxy/requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
asyncpg==0.29.0
python-telegram-bot==20.7
prometheus-client==0.19.0
pydantic==2.5.0
python-dotenv==1.0.0
httpx==0.25.2
```

- [ ] **Step 5: Test configuration loading**

```python
# Test script - run in Python REPL
from config import config

config.validate()
print(f"Proxy port: {config.MCP_PROXY_PORT}")
print(f"WAL dir: {config.WAL_DIR}")
print(f"Retry intervals: {config.RETRY_INTERVAL_1}s, {config.RETRY_INTERVAL_2}s")
```

Expected: No errors, settings loaded

- [ ] **Step 6: Commit**

```bash
git add mcp-proxy/config.py mcp-proxy/models.py mcp-proxy/.env.example mcp-proxy/requirements.txt
git commit -m "feat(mcp-proxy): add configuration and data models

- Config class with environment variable loading
- Pydantic models for all database entities
- Example .env file with all settings
- Python dependencies in requirements.txt"
```

---

### Task 3: Database Connection Pool

**Files:**
- Create: `/root/apps/secureFinanceApp/mcp-proxy/database.py`

**Interfaces:**
- Produces: `DatabasePool` class with methods: `execute()`, `fetch()`, `fetchrow()`, `fetchval()`

- [ ] **Step 1: Write database connection pool**

```python
# /root/apps/secureFinanceApp/mcp-proxy/database.py
"""Database connection pool management."""
import asyncpg
import logging
from typing import Any, Optional, List
from contextlib import asynccontextmanager

from config import config

logger = logging.getLogger(__name__)

class DatabasePool:
    """Async PostgreSQL connection pool."""
    
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create connection pool."""
        logger.info(f"Connecting to database: {config.DATABASE_URL.split('@')[1]}")
        
        self._pool = await asyncpg.create_pool(
            config.DATABASE_URL,
            min_size=config.DATABASE_POOL_MIN,
            max_size=config.DATABASE_POOL_MAX,
            command_timeout=60
        )
        
        logger.info("Database pool created successfully")
    
    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Database pool closed")
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query that doesn't return results."""
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """Fetch all rows."""
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch single row."""
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args, column: int = 0) -> Any:
        """Fetch single value."""
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args, column=column)
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactions."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                yield conn

# Global database instance
db = DatabasePool()
```

- [ ] **Step 2: Write test for database connection**

```python
# Test in Python REPL (after creating .env file)
import asyncio
from database import db

async def test_db():
    await db.connect()
    
    # Test query
    result = await db.fetchval("SELECT COUNT(*) FROM transactions")
    print(f"Transaction count: {result}")
    
    await db.close()

asyncio.run(test_db())
```

Expected: Prints transaction count, no errors

- [ ] **Step 3: Commit**

```bash
git add mcp-proxy/database.py
git commit -m "feat(mcp-proxy): add database connection pool

- Async PostgreSQL connection pool using asyncpg
- Methods for execute, fetch, fetchrow, fetchval
- Transaction context manager
- Connection timeout and pool size configuration"
```

---

### Task 4: Idempotency Handler

**Files:**
- Create: `/root/apps/secureFinanceApp/mcp-proxy/idempotency.py`
- Test: Manual testing in task steps

**Interfaces:**
- Consumes: `DatabasePool` from Task 3
- Produces: `generate_idempotency_key(message, user_id) -> str`, `is_duplicate(key) -> bool`

- [ ] **Step 1: Write idempotency key generation**

```python
# /root/apps/secureFinanceApp/mcp-proxy/idempotency.py
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
```

- [ ] **Step 2: Test idempotency key generation**

```python
# Test in Python REPL
from idempotency import generate_idempotency_key
import time

# Same message, same user, same time bucket
key1 = generate_idempotency_key("Paid 100 for coffee", "user123")
time.sleep(1)
key2 = generate_idempotency_key("Paid 100 for coffee", "user123")

assert key1 == key2, "Same message should generate same key"

# Different message
key3 = generate_idempotency_key("Paid 200 for coffee", "user123")
assert key1 != key3, "Different message should generate different key"

# Different user
key4 = generate_idempotency_key("Paid 100 for coffee", "user456")
assert key1 != key4, "Different user should generate different key"

print("✓ All idempotency tests passed")
```

Expected: All assertions pass

- [ ] **Step 3: Test duplicate detection**

```python
# Test with database
import asyncio
from database import db
from idempotency import is_duplicate

async def test_duplicate():
    await db.connect()
    
    key = "test_duplicate_key_12345"
    
    # Should be unique first time
    is_dup = await is_duplicate(key)
    assert not is_dup, "Should be unique on first check"
    
    # Insert into mcp_call_log
    await db.execute(
        """
        INSERT INTO mcp_call_log (tool_name, params, source, success, idempotency_key)
        VALUES ($1, $2, $3, $4, $5)
        """,
        "test_tool", {}, "test", True, key
    )
    
    # Should be duplicate now
    is_dup = await is_duplicate(key)
    assert is_dup, "Should be duplicate after insert"
    
    await db.close()
    print("✓ Duplicate detection test passed")

asyncio.run(test_duplicate())
```

Expected: Test passes

- [ ] **Step 4: Commit**

```bash
git add mcp-proxy/idempotency.py
git commit -m "feat(mcp-proxy): add idempotency key generation and duplicate detection

- Generate SHA256 keys from message + user + time bucket
- Check mcp_call_log for duplicates within 1 hour
- Return cached responses for duplicate requests
- 5-minute time window for grouping similar messages"
```

---

### Task 5: Write-Ahead Log (WAL)

**Files:**
- Create: `/root/apps/secureFinanceApp/mcp-proxy/wal.py`
- Create: `/root/apps/secureFinanceApp/mcp-proxy/wal/.gitkeep`

**Interfaces:**
- Produces: `append_to_wal(request, idem_key)`, `rotate_old_wal_files()`

- [ ] **Step 1: Write WAL append function**

```python
# /root/apps/secureFinanceApp/mcp-proxy/wal.py
"""Write-ahead log for disaster recovery."""
import json
import os
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Any

from config import config

logger = logging.getLogger(__name__)

async def append_to_wal(
    request_data: Dict[str, Any],
    idempotency_key: str
) -> None:
    """
    Append MCP request to write-ahead log.
    
    Writes to daily log file in JSONL format. Each line is a complete JSON object.
    Forces fsync to ensure data is on disk.
    
    Args:
        request_data: The MCP request dictionary
        idempotency_key: The idempotency key for this request
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "idempotency_key": idempotency_key,
        "request": request_data
    }
    
    # Get today's log file
    log_file = config.WAL_DIR / f"{date.today()}.jsonl"
    
    try:
        # Append to file with fsync
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
            f.flush()
            os.fsync(f.fileno())  # Force write to disk
        
        logger.debug(f"Appended to WAL: {idempotency_key}")
        
    except Exception as e:
        logger.error(f"Failed to write to WAL: {e}")
        # Don't fail the request if WAL write fails
        # WAL is for disaster recovery only

async def rotate_old_wal_files() -> None:
    """
    Delete WAL files older than retention period.
    
    Keeps files within WAL_RETENTION_DAYS, deletes older ones.
    """
    cutoff_date = date.today() - timedelta(days=config.WAL_RETENTION_DAYS)
    deleted_count = 0
    
    try:
        for wal_file in config.WAL_DIR.glob("*.jsonl"):
            # Parse date from filename: YYYY-MM-DD.jsonl
            try:
                file_date = date.fromisoformat(wal_file.stem)
                
                if file_date < cutoff_date:
                    wal_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old WAL file: {wal_file.name}")
                    
            except ValueError:
                # Not a date-formatted file, skip
                continue
        
        if deleted_count > 0:
            logger.info(f"Rotated {deleted_count} old WAL files")
            
    except Exception as e:
        logger.error(f"Error rotating WAL files: {e}")

def get_wal_size_mb() -> float:
    """Get total size of WAL directory in MB."""
    total_bytes = sum(
        f.stat().st_size 
        for f in config.WAL_DIR.glob("*.jsonl")
    )
    return total_bytes / (1024 * 1024)
```

- [ ] **Step 2: Create WAL directory and .gitkeep**

```bash
mkdir -p /root/apps/secureFinanceApp/mcp-proxy/wal
touch /root/apps/secureFinanceApp/mcp-proxy/wal/.gitkeep
```

- [ ] **Step 3: Test WAL writing**

```python
# Test in Python REPL
import asyncio
from wal import append_to_wal, get_wal_size_mb
from pathlib import Path
from config import config

async def test_wal():
    # Append test entry
    test_request = {
        "method": "propose_create_transaction",
        "params": {"description": "test", "amount": 100}
    }
    
    await append_to_wal(test_request, "test_key_12345")
    
    # Check file exists
    today_file = config.WAL_DIR / f"{date.today()}.jsonl"
    assert today_file.exists(), "WAL file should exist"
    
    # Check file contains entry
    with open(today_file) as f:
        lines = f.readlines()
        assert len(lines) > 0, "WAL should have entries"
        
        import json
        entry = json.loads(lines[-1])
        assert entry['idempotency_key'] == "test_key_12345"
    
    # Check size
    size = get_wal_size_mb()
    print(f"WAL size: {size:.2f} MB")
    
    print("✓ WAL test passed")

asyncio.run(test_wal())
```

Expected: Test passes, file created

- [ ] **Step 4: Commit**

```bash
git add mcp-proxy/wal.py mcp-proxy/wal/.gitkeep
git commit -m "feat(mcp-proxy): add write-ahead log for disaster recovery

- Append MCP requests to daily JSONL files
- Force fsync to ensure disk persistence
- Rotate old files based on retention period
- Calculate WAL directory size for monitoring"
```

---

(Task 6-12 continue with similar detail: Circuit Breaker, Telegram Alerter, Checkpoint Handler, Metrics, Retry Worker, Main Server, Systemd Service, Monitoring Scripts, Testing, Documentation, Deployment)

Due to response size limits, I'll complete the remaining tasks in a follow-up. Should I continue with the full plan, or would you like me to save what we have and continue?


### Task 6: Circuit Breaker

**Files:**
- Create: `/root/apps/secureFinanceApp/mcp-proxy/circuit_breaker.py`

**Interfaces:**
- Produces: `CircuitBreaker` class with methods: `record_failure()`, `record_success()`, `should_attempt() -> bool`, `get_state() -> str`

- [ ] **Step 1: Write circuit breaker implementation**

```python
# /root/apps/secureFinanceApp/mcp-proxy/circuit_breaker.py
"""Circuit breaker pattern for backend protection."""
import time
import logging
from enum import Enum

from config import config

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Backend is down, skip calls
    HALF_OPEN = "HALF_OPEN"  # Testing if backend recovered

class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    
    Opens after threshold consecutive failures, preventing further attempts.
    After timeout, enters half-open state to test recovery.
    Closes after successful calls in half-open state.
    """
    
    def __init__(self):
        self.failure_count = 0
        self.success_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
        self.last_state_change = time.time()
    
    def record_failure(self) -> None:
        """Record a failed MCP call."""
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= config.CIRCUIT_BREAKER_THRESHOLD:
                self._open_circuit()
        
        elif self.state == CircuitState.HALF_OPEN:
            # Failed during recovery test, reopen circuit
            self._open_circuit()
    
    def record_success(self) -> None:
        """Record a successful MCP call."""
        self.success_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            # Need 2 successes to close circuit
            if self.success_count >= 2:
                self._close_circuit()
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def should_attempt(self) -> bool:
        """Check if MCP call should be attempted."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout elapsed
            if time.time() - self.last_failure_time > config.CIRCUIT_BREAKER_TIMEOUT:
                self._half_open_circuit()
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def get_state(self) -> str:
        """Get current circuit state."""
        return self.state.value
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_state_change": self.last_state_change
        }
    
    def _open_circuit(self) -> None:
        """Open the circuit (block calls)."""
        logger.error(
            f"Circuit breaker OPENED after {self.failure_count} failures. "
            f"Backend appears to be down."
        )
        self.state = CircuitState.OPEN
        self.last_state_change = time.time()
        self.failure_count = 0
    
    def _half_open_circuit(self) -> None:
        """Enter half-open state (test recovery)."""
        logger.warning("Circuit breaker HALF-OPEN. Testing backend recovery...")
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = time.time()
        self.success_count = 0
    
    def _close_circuit(self) -> None:
        """Close the circuit (normal operation)."""
        logger.info("Circuit breaker CLOSED. Backend recovered.")
        self.state = CircuitState.CLOSED
        self.last_state_change = time.time()
        self.failure_count = 0
        self.success_count = 0

# Global circuit breaker instance
circuit_breaker = CircuitBreaker()
```

- [ ] **Step 2: Test circuit breaker state transitions**

```python
# Test in Python REPL
from circuit_breaker import CircuitBreaker, CircuitState
from config import config

cb = CircuitBreaker()

# Test CLOSED -> OPEN
assert cb.get_state() == "CLOSED"
assert cb.should_attempt() == True

# Record failures
for i in range(config.CIRCUIT_BREAKER_THRESHOLD):
    cb.record_failure()

assert cb.get_state() == "OPEN"
assert cb.should_attempt() == False  # Should block

# Test OPEN -> HALF_OPEN (after timeout)
import time
time.sleep(config.CIRCUIT_BREAKER_TIMEOUT + 1)
assert cb.should_attempt() == True
assert cb.get_state() == "HALF_OPEN"

# Test HALF_OPEN -> CLOSED
cb.record_success()
cb.record_success()
assert cb.get_state() == "CLOSED"

print("✓ Circuit breaker tests passed")
```

Expected: All assertions pass

- [ ] **Step 3: Commit**

```bash
git add mcp-proxy/circuit_breaker.py
git commit -m "feat(mcp-proxy): add circuit breaker for backend protection

- Three states: CLOSED, OPEN, HALF_OPEN
- Opens after threshold consecutive failures
- Tests recovery after timeout period
- Closes after successful recovery test"
```

---

### Task 7: Telegram Alerter

**Files:**
- Create: `/root/apps/secureFinanceApp/mcp-proxy/telegram_alerter.py`

**Interfaces:**
- Consumes: Telegram bot token and chat ID from config
- Produces: `send_failure_alert(pending_tx)`, `send_daily_summary(stats)`

- [ ] **Step 1: Write Telegram alerter**

```python
# /root/apps/secureFinanceApp/mcp-proxy/telegram_alerter.py
"""Send Telegram alerts for failures and summaries."""
import logging
from datetime import datetime
from typing import Dict, Any
from telegram import Bot
from telegram.error import TelegramError

from config import config
from models import PendingTransaction

logger = logging.getLogger(__name__)

class TelegramAlerter:
    """Send alerts via Telegram bot."""
    
    def __init__(self):
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        self.chat_id = config.TELEGRAM_ALERT_CHAT_ID
    
    async def send_failure_alert(self, pending_tx: PendingTransaction) -> bool:
        """
        Send alert for failed transaction after max retries.
        
        Args:
            pending_tx: The failed pending transaction
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Format timestamp in IST
        created_ist = pending_tx.created_at.astimezone()
        
        message = f"""⚠️ Transaction Failed

Message: "{pending_tx.raw_message}"
Attempts: {pending_tx.attempt_count}
Last error: {pending_tx.last_error or 'Unknown error'}
Time: {created_ist.strftime('%Y-%m-%d %H:%M IST')}

Please check system health:
bash /root/system/scripts/check-telegram-sync.sh"""
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Sent failure alert for pending_tx {pending_tx.id}")
            return True
            
        except TelegramError as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
    
    async def send_daily_summary(self, stats: Dict[str, Any]) -> bool:
        """
        Send daily summary report.
        
        Args:
            stats: Dictionary with:
                - successful_count
                - retry_count
                - failed_count
                - success_rate
                - avg_latency_ms
                - wal_size_mb
                - pending_count
                
        Returns:
            True if sent successfully, False otherwise
        """
        from datetime import date
        
        # Format metrics
        success_emoji = "✅" if stats['failed_count'] == 0 else "⚠️"
        health_status = "🟢 Healthy" if stats['success_rate'] >= 99.0 else "🟡 Degraded"
        
        message = f"""📊 Sync Report ({date.today().strftime('%b %d, %Y')})

✅ Successful: {stats['successful_count']} transactions
⚠️ Retried: {stats['retry_count']} (all succeeded)
❌ Failed: {stats['failed_count']}
📈 Success rate: {stats['success_rate']:.1f}%
⏱️ Avg latency: {stats['avg_latency_ms']:.1f}ms
💾 WAL size: {stats['wal_size_mb']:.1f} MB
📋 Pending: {stats['pending_count']}

System: {health_status}"""
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message
            )
            logger.info("Sent daily summary")
            return True
            
        except TelegramError as e:
            logger.error(f"Failed to send daily summary: {e}")
            return False
    
    async def send_admin_alert(self, message: str) -> bool:
        """
        Send custom admin alert.
        
        Args:
            message: Alert message
            
        Returns:
            True if sent successfully
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"⚠️ Admin Alert\n\n{message}"
            )
            return True
        except TelegramError as e:
            logger.error(f"Failed to send admin alert: {e}")
            return False

# Global alerter instance
alerter = TelegramAlerter()
```

- [ ] **Step 2: Test Telegram alert (manual)**

```python
# Test in Python REPL (requires valid bot token and chat ID in .env)
import asyncio
from telegram_alerter import alerter

async def test_alert():
    # Test admin alert
    success = await alerter.send_admin_alert("Test alert from MCP proxy")
    print(f"Alert sent: {success}")
    
    # Test daily summary
    test_stats = {
        'successful_count': 47,
        'retry_count': 3,
        'failed_count': 0,
        'success_rate': 100.0,
        'avg_latency_ms': 1200,
        'wal_size_mb': 2.4,
        'pending_count': 0
    }
    
    success = await alerter.send_daily_summary(test_stats)
    print(f"Summary sent: {success}")

asyncio.run(test_alert())
```

Expected: Receive 2 Telegram messages

- [ ] **Step 3: Commit**

```bash
git add mcp-proxy/telegram_alerter.py
git commit -m "feat(mcp-proxy): add Telegram alerter for failures and summaries

- Send failure alerts after max retries
- Send daily summary reports with stats
- Send custom admin alerts
- Format timestamps in IST"
```

---

### Task 8: Checkpoint Handler

**Files:**
- Create: `/root/apps/secureFinanceApp/mcp-proxy/checkpoint_handler.py`

**Interfaces:**
- Consumes: `DatabasePool` from Task 3
- Produces: `save_checkpoint(data)`, `recover_unprocessed_checkpoints()`

- [ ] **Step 1: Write checkpoint handler**

```python
# /root/apps/secureFinanceApp/mcp-proxy/checkpoint_handler.py
"""Hermes checkpoint save/recovery API."""
import logging
from typing import List
from uuid import UUID

from database import db
from models import CheckpointRequest, HermesCheckpoint

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

async def add_to_retry_queue_from_checkpoint(checkpoint_row: dict) -> None:
    """
    Add checkpoint's pending call to retry queue.
    
    Args:
        checkpoint_row: Checkpoint database row
    """
    pending_call = checkpoint_row['pending_mcp_call']
    
    # Extract workspace and user from conversation state
    conv_state = checkpoint_row['conversation_state']
    # Simplified - would parse from actual state structure
    
    await db.execute(
        """
        INSERT INTO pending_transactions 
            (workspace_id, user_id, telegram_chat_id, raw_message, 
             mcp_tool_name, mcp_params, retry_at, status)
        VALUES ($1, $2, $3, $4, $5, $6, NOW(), 'pending')
        """,
        # Would extract actual IDs from conv_state
        None, None,
        checkpoint_row['telegram_chat_id'],
        "Recovered from checkpoint",
        pending_call.get('tool'),
        pending_call.get('params')
    )
```

- [ ] **Step 2: Test checkpoint save/recovery**

```python
# Test in Python REPL
import asyncio
from database import db
from checkpoint_handler import save_checkpoint, recover_unprocessed_checkpoints
from models import CheckpointRequest

async def test_checkpoint():
    await db.connect()
    
    # Save checkpoint
    checkpoint = CheckpointRequest(
        session_id="test_session_123",
        telegram_chat_id="613463569",
        conversation_state={"messages": []},
        pending_mcp_call={
            "tool": "propose_create_transaction",
            "params": {"description": "test", "amount": 100}
        }
    )
    
    result = await save_checkpoint(checkpoint)
    assert result['status'] == 'saved'
    
    # Check it was saved
    row = await db.fetchrow(
        "SELECT * FROM hermes_checkpoints WHERE session_id = $1",
        "test_session_123"
    )
    assert row is not None
    assert row['processed'] == False
    
    # Test recovery
    count = await recover_unprocessed_checkpoints()
    print(f"Recovered {count} checkpoints")
    
    await db.close()
    print("✓ Checkpoint test passed")

asyncio.run(test_checkpoint())
```

Expected: Checkpoint saved and recovered

- [ ] **Step 3: Commit**

```bash
git add mcp-proxy/checkpoint_handler.py
git commit -m "feat(mcp-proxy): add checkpoint save/recovery handler

- Save Hermes checkpoints via HTTP API
- Recover unprocessed checkpoints on startup
- Check if pending calls were completed
- Add incomplete calls to retry queue"
```

---

(Continuing with remaining tasks in next response due to size...)

### Task 9: Prometheus Metrics

**Files:**
- Create: `/root/apps/secureFinanceApp/mcp-proxy/metrics.py`

**Interfaces:**
- Produces: Prometheus metrics endpoint at `/metrics`

- [ ] **Step 1: Write metrics exporter**

```python
# /root/apps/secureFinanceApp/mcp-proxy/metrics.py
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
```

- [ ] **Step 2: Test metrics**

```python
# Test in Python REPL
import asyncio
from database import db
from metrics import (
    mcp_calls_total, update_metrics, get_metrics_content
)

async def test_metrics():
    await db.connect()
    
    # Increment counter
    mcp_calls_total.labels(tool='propose_create_transaction', status='success').inc()
    mcp_calls_total.labels(tool='propose_create_transaction', status='failure').inc()
    
    # Update gauges
    await update_metrics()
    
    # Get metrics output
    content, content_type = get_metrics_content()
    print(content.decode()[:500])  # Print first 500 chars
    
    assert b'mcp_proxy_calls_total' in content
    assert b'mcp_proxy_retry_queue_size' in content
    
    await db.close()
    print("✓ Metrics test passed")

asyncio.run(test_metrics())
```

Expected: Metrics output in Prometheus format

- [ ] **Step 3: Commit**

```bash
git add mcp-proxy/metrics.py
git commit -m "feat(mcp-proxy): add Prometheus metrics exporter

- Counter for MCP calls by tool and status
- Gauge for retry queue size
- Histogram for call duration
- Gauge for circuit breaker state
- Gauge for WAL size"
```

---

### Task 10: Retry Worker

**Files:**
- Create: `/root/apps/secureFinanceApp/mcp-proxy/retry_worker.py`

**Interfaces:**
- Consumes: `DatabasePool`, `CircuitBreaker`, `TelegramAlerter`
- Produces: Background task that retries pending transactions

- [ ] **Step 1: Write retry worker**

```python
# /root/apps/secureFinanceApp/mcp-proxy/retry_worker.py
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
```

- [ ] **Step 2: Test retry worker (manual)**

```python
# Test by creating a pending transaction and watching it retry
import asyncio
from database import db
from retry_worker import retry_worker

async def test_retry():
    await db.connect()
    
    # Insert test pending transaction
    await db.execute(
        """
        INSERT INTO pending_transactions 
        (workspace_id, user_id, raw_message, mcp_tool_name, mcp_params, retry_at)
        VALUES ($1, $2, $3, $4, $5, NOW())
        """,
        'a9181332-25cb-4b18-a9e1-489eb71ec6c2',
        'a5a07637-b817-43d6-a923-f5cddfbc63d0',
        'Test retry transaction',
        'propose_create_transaction',
        {'description': 'test', 'amount': 100, 'apply': True}
    )
    
    # Start worker
    await retry_worker.start()
    
    # Wait for processing
    await asyncio.sleep(15)
    
    # Check status
    row = await db.fetchrow(
        "SELECT status FROM pending_transactions WHERE raw_message = $1",
        'Test retry transaction'
    )
    print(f"Status: {row['status']}")
    
    await retry_worker.stop()
    await db.close()

asyncio.run(test_retry())
```

Expected: Transaction retried, status updated

- [ ] **Step 3: Commit**

```bash
git add mcp-proxy/retry_worker.py
git commit -m "feat(mcp-proxy): add background retry worker

- Checks for pending transactions every 10 seconds
- Retries with exponential backoff (15s, 30s)
- Respects circuit breaker state
- Sends Telegram alert on final failure
- Updates metrics on success/failure"
```

---

### Task 11: Main FastAPI Server

**Files:**
- Create: `/root/apps/secureFinanceApp/mcp-proxy/server.py`

**Interfaces:**
- Integrates all previous components
- Exposes: POST /mcp, POST /checkpoint, GET /health, GET /metrics

- [ ] **Step 1: Write main server (core functionality)**

```python
# /root/apps/secureFinanceApp/mcp-proxy/server.py
"""Main MCP Proxy Server."""
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import httpx

from config import config
from database import db
from models import MCPRequest, MCPResponse, CheckpointRequest
from idempotency import generate_idempotency_key, is_duplicate, get_cached_response
from circuit_breaker import circuit_breaker
from wal import append_to_wal, rotate_old_wal_files
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
        
        from wal import get_wal_size_mb
        
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
    response: dict = None,
    duration_ms: int = None,
    error: str = None
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
    error: str = None
):
    """Add failed MCP call to retry queue."""
    from datetime import timedelta
    
    retry_at = datetime.utcnow() + timedelta(seconds=config.RETRY_INTERVAL_1)
    
    await db.execute(
        """
        INSERT INTO pending_transactions 
        (workspace_id, user_id, raw_message, mcp_tool_name, mcp_params, 
         idempotency_key, retry_at, last_error, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending')
        """,
        None,  # TODO: Extract workspace_id
        None,  # TODO: Extract user_id
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
```

- [ ] **Step 2: Test server startup**

```bash
cd /root/apps/secureFinanceApp/mcp-proxy
source venv/bin/activate
python server.py
```

Expected: Server starts, health check responds

- [ ] **Step 3: Test endpoints**

```bash
# Health check
curl http://127.0.0.1:8766/health | jq

# Metrics
curl http://127.0.0.1:8766/metrics | head -20
```

Expected: JSON response with stats, Prometheus metrics

- [ ] **Step 4: Commit**

```bash
git add mcp-proxy/server.py
git commit -m "feat(mcp-proxy): add main FastAPI server

- POST /mcp endpoint for proxying MCP calls
- Automatic apply=true injection for propose_* tools
- Idempotency check and caching
- Circuit breaker integration
- Write-ahead log
- POST /checkpoint for Hermes crash recovery
- GET /health with system stats
- GET /metrics for Prometheus
- Background tasks for WAL rotation and metrics"
```

---

### Task 12: Systemd Service and Deployment

**Files:**
- Create: `/root/apps/secureFinanceApp/mcp-proxy/systemd/mcp-proxy.service`
- Create: `/root/apps/secureFinanceApp/mcp-proxy/README.md`
- Create: `/root/apps/secureFinanceApp/mcp-proxy/.env` (from .env.example)

**Interfaces:**
- Produces: Systemd service that starts automatically

- [ ] **Step 1: Write systemd service file**

```ini
# /root/apps/secureFinanceApp/mcp-proxy/systemd/mcp-proxy.service
[Unit]
Description=Securo MCP Proxy Server (Sync Guardian)
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/apps/secureFinanceApp/mcp-proxy
Environment=PATH=/root/apps/secureFinanceApp/mcp-proxy/venv/bin:/usr/local/bin:/usr/bin
EnvironmentFile=/root/apps/secureFinanceApp/mcp-proxy/.env
ExecStart=/root/apps/secureFinanceApp/mcp-proxy/venv/bin/python server.py
Restart=always
RestartSec=10
TimeoutStopSec=30

# Resource limits
MemoryMax=256M
CPUQuota=50%

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Create README.md**

```markdown
# /root/apps/secureFinanceApp/mcp-proxy/README.md
# MCP Proxy Server

Reliability layer between Hermes and Securo MCP for guaranteed transaction sync.

## Features

- Automatic `apply=true` injection
- Persistent retry queue (2 attempts: 15s, 30s)
- Circuit breaker pattern
- Idempotency for duplicate detection
- Write-ahead log for disaster recovery
- Checkpoint API for crash recovery
- Prometheus metrics
- Telegram alerts on failures

## Installation

```bash
# Create virtual environment
cd /root/apps/secureFinanceApp/mcp-proxy
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
docker exec securo-db-1 psql -U postgres -d securo < migrations/001_add_sync_tables.sql

# Configure environment
cp .env.example .env
vim .env  # Add your credentials

# Install systemd service
sudo cp systemd/mcp-proxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mcp-proxy.service
sudo systemctl start mcp-proxy.service
```

## Configuration

Edit `.env` file with your settings. Required variables:

- `SECURO_MCP_TOKEN` - From `/root/apps/hermes-agent/data/profiles/securo/.env`
- `TELEGRAM_BOT_TOKEN` - From same file
- `TELEGRAM_ALERT_CHAT_ID` - Your Telegram chat ID (613463569)

## Deployment

See design spec: `/root/system/docs/2026-09-16-telegram-sync-reliability-design.md`

**Phase 1:** Deploy proxy (no traffic)
**Phase 2:** Switch Hermes to proxy (port 8766)
**Phase 3:** Enable checkpoints

## Monitoring

```bash
# Health check
curl http://127.0.0.1:8766/health | jq

# Prometheus metrics
curl http://127.0.0.1:8766/metrics

# System logs
sudo journalctl -u mcp-proxy.service -f

# Check sync status
bash /root/system/scripts/check-telegram-sync.sh
```

## Troubleshooting

**Proxy won't start:**
- Check `.env` file has all required variables
- Verify database is accessible
- Check logs: `sudo journalctl -u mcp-proxy.service -n 50`

**Transactions not syncing:**
- Check circuit breaker state: `curl http://127.0.0.1:8766/health | jq .circuit_breaker_state`
- Check pending queue: Query `pending_transactions` table
- Verify Hermes is pointing to port 8766

**Circuit breaker opened:**
- Check Securo backend: `docker ps | grep securo-backend`
- Restart backend if needed: `docker restart securo-backend-1`
- Circuit auto-recovers after 60 seconds

## API Endpoints

- `POST /mcp` - Proxy MCP calls
- `POST /checkpoint` - Save Hermes checkpoint
- `GET /health` - Health check with stats
- `GET /metrics` - Prometheus metrics
```

- [ ] **Step 3: Create .env from .env.example**

```bash
cd /root/apps/secureFinanceApp/mcp-proxy

# Copy tokens from Hermes config
HERMES_ENV=/root/apps/hermes-agent/data/profiles/securo/.env
MCP_TOKEN=$(grep SECURO_MCP_TOKEN $HERMES_ENV | cut -d= -f2)
BOT_TOKEN=$(grep TELEGRAM_BOT_TOKEN $HERMES_ENV | cut -d= -f2)

# Create .env
cat > .env << EOF
MCP_PROXY_PORT=8766
HOST=127.0.0.1
SECURO_MCP_URL=http://127.0.0.1:8765/mcp
SECURO_MCP_TOKEN=$MCP_TOKEN
DATABASE_URL=postgresql://postgres:postgres@localhost:15432/securo
TELEGRAM_BOT_TOKEN=$BOT_TOKEN
TELEGRAM_ALERT_CHAT_ID=613463569
RETRY_INTERVAL_1=15
RETRY_INTERVAL_2=30
MAX_RETRIES=2
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60
WAL_DIR=/root/apps/secureFinanceApp/mcp-proxy/wal
LOG_LEVEL=INFO
EOF

chmod 600 .env
```

- [ ] **Step 4: Install systemd service**

```bash
sudo cp /root/apps/secureFinanceApp/mcp-proxy/systemd/mcp-proxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mcp-proxy.service
sudo systemctl start mcp-proxy.service
sudo systemctl status mcp-proxy.service
```

Expected: Service running

- [ ] **Step 5: Test proxy is working**

```bash
# Health check
curl http://127.0.0.1:8766/health | jq

# Should show:
# - status: healthy
# - retry_worker_running: true
# - circuit_breaker_state: CLOSED
```

- [ ] **Step 6: Commit**

```bash
git add mcp-proxy/systemd/ mcp-proxy/README.md
git commit -m "feat(mcp-proxy): add systemd service and deployment docs

- Systemd service with resource limits
- Installation and configuration README
- Deployment instructions
- Troubleshooting guide
- API endpoint documentation"
```

---

### Task 13: Update Hermes Configuration

**Files:**
- Modify: `/root/apps/hermes-agent/data/profiles/securo/.env`
- Modify: `/root/apps/hermes-agent/data/profiles/securo/config.yaml`

**Interfaces:**
- Changes Hermes to point to proxy instead of direct to Securo MCP

- [ ] **Step 1: Backup Hermes config**

```bash
sudo cp /root/apps/hermes-agent/data/profiles/securo/.env /root/apps/hermes-agent/data/profiles/securo/.env.backup
sudo cp /root/apps/hermes-agent/data/profiles/securo/config.yaml /root/apps/hermes-agent/data/profiles/securo/config.yaml.backup
```

- [ ] **Step 2: Update SECURO_MCP_URL**

```bash
sudo sed -i 's|SECURO_MCP_URL=http://127.0.0.1:8765/mcp|SECURO_MCP_URL=http://127.0.0.1:8766/mcp|' /root/apps/hermes-agent/data/profiles/securo/.env
```

- [ ] **Step 3: Verify change**

```bash
grep SECURO_MCP_URL /root/apps/hermes-agent/data/profiles/securo/.env
```

Expected: Shows port 8766

- [ ] **Step 4: Add checkpoint hook to config.yaml**

```bash
sudo tee -a /root/apps/hermes-agent/data/profiles/securo/config.yaml > /dev/null << 'EOF'

# MCP Proxy checkpoint integration
hooks:
  pre_mcp_call:
    enabled: true
    url: http://127.0.0.1:8766/checkpoint
    timeout: 5
EOF
```

- [ ] **Step 5: Restart Hermes**

```bash
sudo systemctl restart hermes-gateway-securo.service
sleep 5
sudo systemctl status hermes-gateway-securo.service
```

Expected: Hermes running, no errors

- [ ] **Step 6: Verify Hermes is using proxy**

```bash
# Wait 30 seconds for Hermes to connect

# Check MCP call log
docker exec securo-db-1 psql -U postgres -d securo -c "SELECT COUNT(*) FROM mcp_call_log WHERE source='hermes';"

# Should show calls from Hermes through proxy
```

- [ ] **Step 7: Document change**

```bash
cat >> /root/system/docs/TELEGRAM-SECURO-SYNC.md << 'EOF'

## Configuration Update (2026-09-16)

Hermes now routes through MCP proxy for sync reliability:

- **Old:** Hermes → Securo MCP (port 8765)
- **New:** Hermes → MCP Proxy (port 8766) → Securo MCP (port 8765)

To rollback:
```bash
sudo sed -i 's|8766|8765|' /root/apps/hermes-agent/data/profiles/securo/.env
sudo systemctl restart hermes-gateway-securo.service
```
EOF
```

- [ ] **Step 8: Commit**

```bash
cd /root/system
git add docs/TELEGRAM-SECURO-SYNC.md
git commit -m "docs: update Hermes configuration to use MCP proxy

- Hermes now points to port 8766 (proxy)
- Added checkpoint hook for crash recovery
- Documented rollback procedure"
```

---

### Task 14: Integration Testing

**Files:**
- Create: `/root/apps/secureFinanceApp/mcp-proxy/tests/integration_test.sh`

**Interfaces:**
- Tests all 12 scenarios from design spec

- [ ] **Step 1: Write integration test script**

```bash
# /root/apps/secureFinanceApp/mcp-proxy/tests/integration_test.sh
#!/bin/bash
set -e

echo "=== MCP Proxy Integration Tests ==="
echo ""

# Test 1: Normal transaction
echo "Test 1: Normal transaction"
# Send via Telegram: "Integration test 1 - Paid 100 for test"
read -p "Send test transaction via Telegram, then press Enter..."

sleep 5
RESULT=$(docker exec securo-db-1 psql -U postgres -d securo -t -c \
  "SELECT COUNT(*) FROM transactions WHERE description LIKE '%Integration test 1%'")

if [ "$RESULT" -ge 1 ]; then
  echo "✓ Test 1 passed: Transaction created"
else
  echo "✗ Test 1 failed: Transaction not found"
  exit 1
fi

# Test 2: Retry on failure
echo ""
echo "Test 2: Retry on failure"
echo "Stopping backend..."
docker stop securo-backend-1

echo "Send transaction via Telegram: 'Integration test 2 - Paid 200 retry test'"
read -p "Press Enter after sending..."

sleep 5
PENDING=$(docker exec securo-db-1 psql -U postgres -d securo -t -c \
  "SELECT COUNT(*) FROM pending_transactions WHERE raw_message LIKE '%test 2%'")

if [ "$PENDING" -ge 1 ]; then
  echo "✓ Pending transaction created"
else
  echo "✗ Failed to create pending transaction"
  exit 1
fi

echo "Starting backend..."
docker start securo-backend-1

echo "Waiting 50 seconds for retries..."
sleep 50

STATUS=$(docker exec securo-db-1 psql -U postgres -d securo -t -c \
  "SELECT status FROM pending_transactions WHERE raw_message LIKE '%test 2%' LIMIT 1")

if [[ "$STATUS" == *"success"* ]]; then
  echo "✓ Test 2 passed: Transaction succeeded after retry"
else
  echo "✗ Test 2 failed: Status = $STATUS"
  exit 1
fi

# Test 3: Duplicate prevention
echo ""
echo "Test 3: Duplicate prevention"
echo "Send SAME message twice: 'Integration test 3 - Paid 300 duplicate'"
read -p "Press Enter after sending first..."
sleep 2
read -p "Press Enter after sending second (same message)..."
sleep 5

COUNT=$(docker exec securo-db-1 psql -U postgres -d securo -t -c \
  "SELECT COUNT(*) FROM transactions WHERE description LIKE '%test 3%'")

if [ "$COUNT" -eq 1 ]; then
  echo "✓ Test 3 passed: Only 1 transaction created (duplicate prevented)"
else
  echo "✗ Test 3 failed: Found $COUNT transactions"
  exit 1
fi

# Test 4: Health check
echo ""
echo "Test 4: Health check"
HEALTH=$(curl -s http://127.0.0.1:8766/health)
echo "$HEALTH" | jq

STATUS=$(echo "$HEALTH" | jq -r .status)
if [ "$STATUS" == "healthy" ]; then
  echo "✓ Test 4 passed: Proxy is healthy"
else
  echo "✗ Test 4 failed: Status = $STATUS"
  exit 1
fi

# Test 5: Metrics
echo ""
echo "Test 5: Prometheus metrics"
METRICS=$(curl -s http://127.0.0.1:8766/metrics)

if echo "$METRICS" | grep -q "mcp_proxy_calls_total"; then
  echo "✓ Test 5 passed: Metrics endpoint working"
else
  echo "✗ Test 5 failed: Metrics not found"
  exit 1
fi

echo ""
echo "=== All integration tests passed! ==="
```

- [ ] **Step 2: Make script executable and run**

```bash
chmod +x /root/apps/secureFinanceApp/mcp-proxy/tests/integration_test.sh
bash /root/apps/secureFinanceApp/mcp-proxy/tests/integration_test.sh
```

Expected: All tests pass

- [ ] **Step 3: Document test results**

Create `/root/system/docs/MCP-PROXY-TEST-RESULTS.md` with:
- Date tested
- All test results
- Any issues encountered
- Performance metrics observed

- [ ] **Step 4: Commit**

```bash
git add mcp-proxy/tests/
git commit --trailer "Co-authored-by: Cursor <cursoragent@cursor.com>" -m "test(mcp-proxy): add integration test suite

- Test normal transaction flow
- Test retry on backend failure
- Test duplicate prevention
- Test health check endpoint
- Test Prometheus metrics"
```

---

### Task 15: Monitoring Setup

**Files:**
- Update: `/root/system/scripts/check-telegram-sync.sh`
- Create: `/root/system/scripts/daily-summary-cron.sh`
- Create: Cron job for daily reconciliation

**Interfaces:**
- Enhanced monitoring scripts

- [ ] **Step 1: Update check-telegram-sync.sh**

```bash
# Already created in earlier troubleshooting, verify it includes MCP proxy checks
cat /root/system/scripts/check-telegram-sync.sh

# Should include:
# - MCP proxy health check
# - Pending transactions count
# - Recent MCP calls
# - Failed transactions last 24h
```

- [ ] **Step 2: Create daily summary trigger script**

```bash
cat > /root/system/scripts/daily-summary-cron.sh << 'EOF'
#!/bin/bash
# Trigger daily summary from MCP proxy

curl -X POST http://127.0.0.1:8766/send-daily-summary
EOF

chmod +x /root/system/scripts/daily-summary-cron.sh
```

- [ ] **Step 3: Set up cron jobs**

```bash
# Add to root's crontab
sudo crontab -e

# Add these lines:
# Daily summary at 8 AM
0 8 * * * /root/system/scripts/daily-summary-cron.sh

# Daily reconciliation at 2 AM
0 2 * * * /root/system/scripts/daily-reconciliation.sh
```

- [ ] **Step 4: Test daily summary manually**

```bash
curl -X POST http://127.0.0.1:8766/send-daily-summary
```

Expected: Receive Telegram message with summary

- [ ] **Step 5: Commit**

```bash
git add system/scripts/daily-summary-cron.sh
git commit --trailer "Co-authored-by: Cursor <cursoragent@cursor.com>" -m "feat(monitoring): add cron jobs for daily summary and reconciliation

- Daily summary at 8 AM via Telegram
- Daily reconciliation at 2 AM
- Manual trigger scripts"
```

---

## Final Steps

### Pre-Launch Checklist

- [ ] All database migrations run successfully
- [ ] MCP proxy service running and healthy
- [ ] Hermes pointing to proxy (port 8766)
- [ ] Send test transaction, verify it appears in database
- [ ] Check mcp_call_log shows `params_modified=true`
- [ ] Stop backend, send transaction, verify retry works
- [ ] Verify Telegram alert received on final failure
- [ ] Health check returns healthy status
- [ ] Prometheus metrics accessible
- [ ] Daily summary received via Telegram
- [ ] All integration tests pass
- [ ] Documentation complete and committed

### Rollback Procedure

If issues arise:

```bash
# Stop proxy
sudo systemctl stop mcp-proxy.service

# Point Hermes back to Securo MCP
sudo sed -i 's|8766|8765|' /root/apps/hermes-agent/data/profiles/securo/.env
sudo systemctl restart hermes-gateway-securo.service

# Verify direct connection works
# Send test transaction via Telegram
```

### Success Metrics

Monitor for 24 hours after deployment:

- [ ] 100% of transactions synced (check daily summary)
- [ ] <2s median latency (check metrics)
- [ ] Zero undetected failures (all failures alerted)
- [ ] Retry worker stable (no crashes)
- [ ] Memory usage <256MB
- [ ] No circuit breaker openings (unless backend actually down)

---

## Plan Review Checklist

Before implementation:

- [ ] All file paths are correct and consistent
- [ ] Database schema matches models
- [ ] API interfaces between components are clear
- [ ] Configuration variables are complete
- [ ] Error handling is comprehensive
- [ ] Logging is sufficient for debugging
- [ ] Tests cover main scenarios
- [ ] Documentation explains how to operate the system
- [ ] Rollback procedure is clear
- [ ] Dependencies are specified with versions

---

**Plan complete and saved to `docs/superpowers/plans/2026-09-16-telegram-sync-reliability.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
