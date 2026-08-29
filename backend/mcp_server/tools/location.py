"""Last-known device location for Finance Orbit.

record_location writes immediately (not a money mutation). Manual
transactions pick the area up automatically via create_transaction.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import location_service
from mcp_server.auth import CallContext
from mcp_server.registry import tool


@tool(
    name="get_last_location",
    description=(
        "Return the user's last known device location (area name, age in "
        "minutes, lat/lon) if it is still fresh. Used to see where a "
        "manual transaction will be tagged. Do not invent a place if this "
        "returns empty."
    ),
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
    tags=["read", "location"],
)
async def get_last_location(*, session: AsyncSession, ctx: CallContext) -> dict[str, Any]:
    loc = await location_service.get_last_location(session, ctx.user_id)
    if loc is None:
        return {"location": None, "fresh": False}
    return {
        "location": {
            "area": loc.get("area"),
            "lat": loc.get("lat"),
            "lon": loc.get("lon"),
            "accuracy_m": loc.get("accuracy_m"),
            "source": loc.get("source"),
            "recorded_at": loc.get("recorded_at"),
            "age_minutes": loc.get("age_minutes"),
        },
        "fresh": True,
    }


@tool(
    name="record_location",
    description=(
        "Store the user's current device location (from a Telegram pin or "
        "live location). Writes immediately — not a propose_* tool. "
        "Later manual transactions are auto-tagged with this area while "
        "the fix is fresh. Pass latitude and longitude from the pin; do "
        "not guess coordinates."
    ),
    parameters={
        "type": "object",
        "properties": {
            "latitude": {"type": "number"},
            "longitude": {"type": "number"},
            "accuracy_m": {"type": "number"},
            "area": {
                "type": "string",
                "description": "Optional already-resolved place name; otherwise Nominatim fills it",
            },
            "source": {"type": "string", "default": "telegram"},
        },
        "required": ["latitude", "longitude"],
        "additionalProperties": False,
    },
    tags=["write", "location"],
)
async def record_location(
    *,
    session: AsyncSession,
    ctx: CallContext,
    latitude: float,
    longitude: float,
    accuracy_m: float | None = None,
    area: str | None = None,
    source: str = "telegram",
) -> dict[str, Any]:
    try:
        loc = await location_service.record_location(
            session,
            ctx.user_id,
            float(latitude),
            float(longitude),
            accuracy_m=accuracy_m,
            source=source or "telegram",
            area=area,
        )
    except ValueError as exc:
        return {"error": str(exc)}
    return {"ok": True, "location": loc}
