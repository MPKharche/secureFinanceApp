#!/usr/bin/env python3
"""Mint a revocable external MCP JWT for Finance Orbit (run inside securo-backend)."""
import asyncio
from uuid import UUID

from app.agents.config import get_agent_settings
from app.agents.services.mcp_token_store import issue_external_token
from app.core.database import async_session_maker

USER_ID = UUID("a5a07637-b817-43d6-a923-f5cddfbc63d0")
WORKSPACE_ID = UUID("a9181332-25cb-4b18-a9e1-489eb71ec6c2")


async def _mint() -> str:
    s = get_agent_settings()
    async with async_session_maker() as session:
        token, _row = await issue_external_token(
            session,
            user_id=USER_ID,
            workspace_id=WORKSPACE_ID,
            ttl_seconds=max(s.mcp_external_ttl_days, 1) * 86400,
            label="Finance Orbit",
        )
    return token


if __name__ == "__main__":
    print(asyncio.run(_mint()))
