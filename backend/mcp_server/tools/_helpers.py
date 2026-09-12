"""Shared helpers for serializing model rows into LLM-friendly dicts.

Keep payloads small and stable: a transaction returned to the LLM should
have a small set of obviously-named fields, not the full SQLAlchemy row.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

logger = logging.getLogger(__name__)


def parse_date(v: Any) -> Optional[date]:
    if v is None or v == "":
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    return date.fromisoformat(str(v))


def parse_uuid(v: Any) -> Optional[uuid.UUID]:
    """Parse a UUID, or return None for empty/invalid input.

    Callers that require a hard error should check for None after parsing.
    """
    if v is None or v == "":
        return None
    if isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(str(v))
    except (ValueError, TypeError, AttributeError):
        logger.debug("parse_uuid: ignoring non-UUID value %r", v)
        return None


def parse_uuid_list(v: Any) -> Optional[list[uuid.UUID]]:
    """Parse one or more UUID strings; skip empties and invalid entries.

    A bare non-UUID string (e.g. an account/category name) is treated as
    a single-element list and does not crash. If the input was non-empty
    but every entry failed to parse, raise ValueError so agents get
    feedback instead of a silent empty filter.
    """
    if v is None:
        return None
    values = v if isinstance(v, (list, tuple)) else [v]
    raw = [x for x in values if x is not None and x != ""]
    if not raw:
        return None
    parsed: list[uuid.UUID] = []
    invalid: list[Any] = []
    for x in raw:
        u = parse_uuid(x)
        if u is not None:
            parsed.append(u)
        else:
            invalid.append(x)
    if not parsed and invalid:
        raise ValueError(
            f"ids must be UUID(s), got non-UUID values: {invalid!r}"
        )
    return parsed or None


def num(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, Decimal):
        return float(x)
    return float(x)


async def resolve_workspace_id(session, ctx) -> uuid.UUID:
    """Return the workspace the call operates in.

    Prefer the explicit `ws_id` claim from the JWT. Fall back to the
    caller's default (first) workspace — supports tokens minted before
    the workspace migration AND keeps single-workspace callers free of
    having to specify a workspace.
    """
    if ctx.workspace_id is not None:
        return ctx.workspace_id
    from app.services.workspace_service import get_default_workspace

    ws = await get_default_workspace(session, ctx.user_id)
    if ws is None:
        raise ValueError("No workspace available for this user")
    return ws.id
