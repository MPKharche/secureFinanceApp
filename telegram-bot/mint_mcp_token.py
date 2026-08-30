#!/usr/bin/env python3
"""Mint a 90-day external MCP JWT for the Telegram bot (run inside securo-backend)."""
from uuid import UUID

from app.agents.mcp.auth import mint_token

USER_ID = UUID("a5a07637-b817-43d6-a923-f5cddfbc63d0")
WORKSPACE_ID = UUID("a9181332-25cb-4b18-a9e1-489eb71ec6c2")

if __name__ == "__main__":
    print(
        mint_token(
            user_id=USER_ID,
            workspace_id=WORKSPACE_ID,
            ttl_seconds=90 * 86400,
            external=True,
        )
    )
