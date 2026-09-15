-- MCP Proxy Sync Tables Migration
-- Creates tables for sync reliability: pending_transactions, mcp_call_log, hermes_checkpoints

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
