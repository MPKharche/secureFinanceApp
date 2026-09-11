"""Issue, list, and revoke external MCP JWTs."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.mcp.auth import JWT_ALGO, mint_token
from app.agents.models.mcp_token import McpIssuedToken, McpTokenDenylist


def token_sha256(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _unverified_claims(token: str) -> dict:
    return jwt.get_unverified_claims(token)


async def issue_external_token(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    workspace_id: Optional[uuid.UUID],
    ttl_seconds: int,
    label: str = "external",
) -> tuple[str, McpIssuedToken]:
    token = mint_token(
        user_id=user_id,
        workspace_id=workspace_id,
        ttl_seconds=ttl_seconds,
        external=True,
    )
    claims = _unverified_claims(token)
    jti = uuid.UUID(str(claims["jti"]))
    exp = datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc)
    row = McpIssuedToken(
        jti=jti,
        token_hash=token_sha256(token),
        user_id=user_id,
        workspace_id=workspace_id,
        label=label[:120],
        expires_at=exp,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return token, row


async def list_tokens(session: AsyncSession, user_id: uuid.UUID) -> list[McpIssuedToken]:
    result = await session.execute(
        select(McpIssuedToken)
        .where(McpIssuedToken.user_id == user_id)
        .order_by(McpIssuedToken.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_issued(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_id: uuid.UUID,
    reason: str = "user_revoke",
) -> bool:
    row = await session.get(McpIssuedToken, token_id)
    if row is None or row.user_id != user_id:
        return False
    now = datetime.now(timezone.utc)
    if row.revoked_at is None:
        row.revoked_at = now
    denylist = await session.get(McpTokenDenylist, row.token_hash)
    if denylist is None:
        session.add(
            McpTokenDenylist(
                token_hash=row.token_hash,
                jti=str(row.jti),
                reason=reason,
                revoked_at=now,
                expires_at=row.expires_at,
            )
        )
    await session.commit()
    return True


async def denylist_raw_token(
    session: AsyncSession,
    token: str,
    *,
    reason: str = "rotated",
) -> None:
    """Ban a JWT by hash so legacy (no-jti) tokens die after a handoff."""
    digest = token_sha256(token)
    existing = await session.get(McpTokenDenylist, digest)
    if existing is not None:
        return
    claims = _unverified_claims(token)
    exp_raw = claims.get("exp")
    expires_at = (
        datetime.fromtimestamp(int(exp_raw), tz=timezone.utc)
        if isinstance(exp_raw, (int, float))
        else datetime.now(timezone.utc) + timedelta(days=90)
    )
    jti = claims.get("jti")
    session.add(
        McpTokenDenylist(
            token_hash=digest,
            jti=str(jti) if jti else None,
            reason=reason,
            expires_at=expires_at,
        )
    )
    if jti:
        result = await session.execute(select(McpIssuedToken).where(McpIssuedToken.jti == uuid.UUID(str(jti))))
        issued = result.scalar_one_or_none()
        if issued is not None and issued.revoked_at is None:
            issued.revoked_at = datetime.now(timezone.utc)
    await session.commit()


async def is_revoked(session: AsyncSession, token: str, jti: Optional[str]) -> bool:
    digest = token_sha256(token)
    banned = await session.get(McpTokenDenylist, digest)
    if banned is not None:
        return True
    clauses = [McpIssuedToken.token_hash == digest]
    if jti:
        try:
            clauses.append(McpIssuedToken.jti == uuid.UUID(str(jti)))
        except ValueError:
            pass
        denylist_jti = await session.execute(
            select(McpTokenDenylist).where(McpTokenDenylist.jti == str(jti))
        )
        if denylist_jti.scalar_one_or_none() is not None:
            return True
    result = await session.execute(select(McpIssuedToken).where(or_(*clauses)))
    row = result.scalar_one_or_none()
    if row is None:
        return False
    if row.revoked_at is not None:
        return True
    row.last_used_at = datetime.now(timezone.utc)
    return False
