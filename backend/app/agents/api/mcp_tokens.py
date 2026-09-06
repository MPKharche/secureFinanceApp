"""Mint, list, and revoke long-lived MCP tokens for external agents.

Lets a logged-in user generate a JWT they can paste into Claude Desktop,
n8n, or any other MCP client. Tokens are signed with `AGENTS_MCP_JWT_SECRET`,
scoped to the calling user AND their active workspace, stored by hash so
they can be revoked, and carry an `ext: true` claim plus `jti`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.config import get_agent_settings
from app.agents.services.mcp_token_store import issue_external_token, list_tokens, revoke_issued
from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_writable_workspace

router = APIRouter(prefix="/api/agents/mcp-tokens", tags=["agents"])


class TokenMeta(BaseModel):
    id: uuid.UUID
    jti: uuid.UUID
    label: str
    workspace_id: uuid.UUID | None
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_mcp_token(
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
    label: str = Query(default="external", max_length=120),
):
    """Mint a long-lived MCP token for an external client.

    Write-gated because of what the token can do, not because minting
    writes a row. It carries (user, workspace) to the MCP server, whose
    tool set includes `propose_create_transaction`, `propose_create_budget`
    and friends — all of which persist. Handing a read-only member a
    credential that writes would route around the gate the HTTP API
    enforces.

    The raw JWT is returned once. Subsequent GETs only show metadata.
    """
    s = get_agent_settings()
    ttl_seconds = max(s.mcp_external_ttl_days, 1) * 86400
    token, row = await issue_external_token(
        session,
        user_id=ctx.user_id,
        workspace_id=ctx.workspace.id,
        ttl_seconds=ttl_seconds,
        label=label or "external",
    )
    return {
        "id": str(row.id),
        "jti": str(row.jti),
        "token": token,
        "label": row.label,
        "expires_in_seconds": ttl_seconds,
        "expires_in_days": s.mcp_external_ttl_days,
        "expires_at": row.expires_at.astimezone(timezone.utc).isoformat(),
        "workspace_id": str(ctx.workspace.id),
        "workspace_name": ctx.workspace.name,
    }


@router.get("", response_model=list[TokenMeta])
async def list_mcp_tokens(
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    rows = await list_tokens(session, ctx.user_id)
    return [
        TokenMeta(
            id=row.id,
            jti=row.jti,
            label=row.label,
            workspace_id=row.workspace_id,
            created_at=row.created_at,
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
            last_used_at=row.last_used_at,
        )
        for row in rows
    ]


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_mcp_token(
    token_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    ok = await revoke_issued(session, user_id=ctx.user_id, token_id=token_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
