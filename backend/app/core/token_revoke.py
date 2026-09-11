"""JWT denylist (web access tokens).

FastAPI Users' default JWT strategy cannot destroy tokens. We stamp a `jti`
on issue and record it in Redis on logout for the remaining lifetime so
stolen Bearer tokens stop working immediately instead of lingering 24h.
Pre-jti tokens are denylisted by sha256(token).
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

from fastapi_users.jwt import decode_jwt

from app.core.config import get_settings
from app.core.redis import get_redis

_JTI_PREFIX = "jwt_revoked:"
_HASH_PREFIX = "jwt_revoked_hash:"
_AUDIENCE = ["fastapi-users:auth"]


def token_sha256(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _ttl_from_payload(payload: dict[str, Any]) -> int:
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        settings = get_settings()
        return max(int(settings.access_token_expire_minutes * 60), 1)
    return max(int(exp - time.time()), 1)


async def revoke_access_token(token: str) -> None:
    if not token:
        return
    settings = get_settings()
    secret = settings.secret_key.get_secret_value()
    try:
        payload = decode_jwt(token, secret, _AUDIENCE, algorithms=["HS256"])
    except Exception:
        # Still hash-ban an unreadable token so a replay of the raw string dies.
        payload = {}
    r = await get_redis()
    ttl = _ttl_from_payload(payload)
    digest = token_sha256(token)
    await r.set(f"{_HASH_PREFIX}{digest}", "1", ex=ttl)
    jti = payload.get("jti")
    if isinstance(jti, str) and jti:
        await r.set(f"{_JTI_PREFIX}{jti}", "1", ex=ttl)


async def is_access_token_revoked(token: str, payload: dict[str, Any]) -> bool:
    r = await get_redis()
    digest = token_sha256(token)
    if await r.exists(f"{_HASH_PREFIX}{digest}"):
        return True
    jti = payload.get("jti")
    if isinstance(jti, str) and jti and await r.exists(f"{_JTI_PREFIX}{jti}"):
        return True
    return False
