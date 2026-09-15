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
