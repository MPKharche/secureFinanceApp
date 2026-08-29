"""Last-known device location for auto-tagging manual transactions.

Telegram cannot attach GPS to every chat message. Phone apps (OwnTracks)
and occasional Telegram pins/live-location write the latest fix here.
Manual transaction creates then append a short 📍 area note when the fix
is still fresh.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.models.user import User

logger = logging.getLogger(__name__)

PREF_KEY = "last_location"
NOTES_MAX = 1000
_GEOCODE_PRECISION = 3  # ~110m; reuse area if we haven't moved that far


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def format_area(address: dict[str, Any]) -> Optional[str]:
    suburb = (
        address.get("suburb")
        or address.get("neighbourhood")
        or address.get("neighborhood")
        or address.get("village")
        or address.get("hamlet")
        or address.get("city_district")
    )
    city = (
        address.get("city")
        or address.get("town")
        or address.get("municipality")
        or address.get("county")
    )
    if suburb and city and suburb.strip().lower() != city.strip().lower():
        return f"{suburb.strip()}, {city.strip()}"
    return (city or suburb or address.get("state") or None)


def loc_tag(area: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", area.lower()).strip("-")
    return f"#loc-{slug[:40]}" if slug else "#loc"


def stamp_notes(notes: Optional[str], loc: dict[str, Any]) -> Optional[str]:
    """Append 📍 area + #loc-… if notes do not already carry a location."""
    area = (loc.get("area") or "").strip()
    if not area:
        lat = loc.get("lat")
        lon = loc.get("lon")
        if lat is None or lon is None:
            return notes
        area = f"{float(lat):.4f},{float(lon):.4f}"
    tag = loc_tag(area)
    marker = f"📍 {area}"
    existing = notes or ""
    if "📍" in existing or tag in existing:
        return notes
    extra = f"{marker} {tag}"
    combined = f"{existing.rstrip()} {extra}".strip() if existing.strip() else extra
    if len(combined) <= NOTES_MAX:
        return combined
    combined = f"{existing.rstrip()} {marker}".strip() if existing.strip() else marker
    if len(combined) <= NOTES_MAX:
        return combined
    return notes


async def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    settings = get_settings()
    url = (settings.nominatim_url or "").strip()
    if not url:
        return None
    headers = {
        "User-Agent": settings.nominatim_user_agent,
        "Accept-Language": "en",
    }
    params = {
        "lat": f"{lat:.6f}",
        "lon": f"{lon:.6f}",
        "format": "jsonv2",
        "zoom": 16,
        "addressdetails": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
    except Exception:
        logger.warning("Nominatim reverse geocode failed for %s,%s", lat, lon, exc_info=True)
        return None
    if not isinstance(data, dict):
        return None
    return format_area(data.get("address") or {})


def _reuse_area(last: dict[str, Any], lat: float, lon: float) -> Optional[str]:
    try:
        same = (
            round(float(last["lat"]), _GEOCODE_PRECISION) == round(lat, _GEOCODE_PRECISION)
            and round(float(last["lon"]), _GEOCODE_PRECISION) == round(lon, _GEOCODE_PRECISION)
        )
    except (KeyError, TypeError, ValueError):
        return None
    if same:
        area = (last.get("area") or "").strip()
        return area or None
    return None


async def record_location(
    session: AsyncSession,
    user_id: uuid.UUID,
    lat: float,
    lon: float,
    *,
    accuracy_m: float | None = None,
    source: str = "owntracks",
    recorded_at: datetime | None = None,
    area: str | None = None,
) -> dict[str, Any]:
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("invalid coordinates")

    user = await session.get(User, user_id)
    if user is None:
        raise ValueError("user not found")

    when = recorded_at or _utcnow()
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    when = when.astimezone(timezone.utc)
    if when > _utcnow():
        when = _utcnow()

    prefs = dict(user.preferences or {})
    last = prefs.get(PREF_KEY) if isinstance(prefs.get(PREF_KEY), dict) else {}
    resolved_area = (area or "").strip() or _reuse_area(last or {}, lat, lon)
    if not resolved_area:
        resolved_area = await reverse_geocode(lat, lon)

    loc = {
        "lat": round(float(lat), 6),
        "lon": round(float(lon), 6),
        "accuracy_m": round(float(accuracy_m), 1) if accuracy_m is not None else None,
        "area": resolved_area,
        "source": (source or "owntracks")[:40],
        "recorded_at": when.isoformat(),
    }
    prefs[PREF_KEY] = loc
    user.preferences = prefs
    flag_modified(user, "preferences")
    await session.commit()
    await session.refresh(user)
    return loc


def _age_minutes(loc: dict[str, Any]) -> Optional[int]:
    recorded = _parse_iso(loc.get("recorded_at"))
    if recorded is None:
        return None
    delta = _utcnow() - recorded
    return max(0, int(delta.total_seconds() // 60))


async def get_last_location(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    max_age_minutes: int | None = None,
) -> Optional[dict[str, Any]]:
    settings = get_settings()
    limit = settings.location_max_age_minutes if max_age_minutes is None else max_age_minutes
    user = await session.get(User, user_id)
    if user is None:
        return None
    raw = (user.preferences or {}).get(PREF_KEY)
    if not isinstance(raw, dict) or raw.get("lat") is None or raw.get("lon") is None:
        return None
    loc = dict(raw)
    age = _age_minutes(loc)
    loc["age_minutes"] = age
    loc["stale"] = age is None or age > limit
    if loc["stale"]:
        return None
    return loc


async def with_fresh_location_note(
    session: AsyncSession,
    user_id: uuid.UUID,
    notes: Optional[str],
) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    settings = get_settings()
    if not settings.location_auto_stamp:
        return notes, None
    loc = await get_last_location(session, user_id)
    if loc is None:
        return notes, None
    return stamp_notes(notes, loc), loc
