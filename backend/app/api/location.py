"""Device location ingest (OwnTracks / Hermes webhook) and last-fix reads."""
from __future__ import annotations

import base64
import hmac
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_async_session
from app.services import location_service

router = APIRouter(prefix="/api/location", tags=["location"])


def _extract_token(authorization: Optional[str], token: Optional[str]) -> Optional[str]:
    if token and token.strip():
        return token.strip()
    if not authorization:
        return None
    kind, _, rest = authorization.partition(" ")
    rest = rest.strip()
    if kind.lower() == "bearer":
        return rest or None
    if kind.lower() == "basic" and rest:
        try:
            decoded = base64.b64decode(rest).decode()
        except Exception:
            return None
        if ":" in decoded:
            _user, password = decoded.split(":", 1)
            return password
        return decoded
    return None


def _ingest_user_id() -> uuid.UUID:
    settings = get_settings()
    raw = (settings.location_ingest_user_id or "").strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="location ingest user not configured",
        )
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="location ingest user id is invalid",
        ) from exc


def _require_ingest_token(
    authorization: Optional[str],
    token: Optional[str],
) -> None:
    settings = get_settings()
    expected = (settings.location_ingest_token or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="location ingest not configured",
        )
    provided = _extract_token(authorization, token)
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _point_from_payload(payload: Any) -> Optional[dict[str, Any]]:
    """Accept OwnTracks JSON, a list of those, or a generic {lat,lon} body."""
    if isinstance(payload, list):
        points = [_point_from_payload(item) for item in payload]
        points = [p for p in points if p is not None]
        return points[-1] if points else None
    if not isinstance(payload, dict):
        return None
    kind = payload.get("_type")
    if kind and kind not in ("location", "waypoint"):
        return None
    lat = _as_float(payload.get("lat") if "lat" in payload else payload.get("latitude"))
    lon = _as_float(payload.get("lon") if "lon" in payload else payload.get("longitude"))
    if lat is None or lon is None:
        return None
    acc = _as_float(payload.get("acc") if "acc" in payload else payload.get("accuracy_m"))
    recorded_at = None
    tst = payload.get("tst")
    if tst is not None:
        try:
            recorded_at = datetime.fromtimestamp(float(tst), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            recorded_at = None
    source = str(payload.get("source") or ("owntracks" if kind else "http"))
    area = payload.get("area")
    return {
        "lat": lat,
        "lon": lon,
        "accuracy_m": acc,
        "source": source,
        "recorded_at": recorded_at,
        "area": area if isinstance(area, str) else None,
    }


@router.post("/ingest")
@router.post("/owntracks")
async def ingest_location(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
):
    _require_ingest_token(authorization, token)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid json") from exc

    point = _point_from_payload(payload)
    if point is None:
        return {"ok": True, "ignored": True}

    try:
        loc = await location_service.record_location(
            session,
            _ingest_user_id(),
            point["lat"],
            point["lon"],
            accuracy_m=point.get("accuracy_m"),
            source=point.get("source") or "owntracks",
            recorded_at=point.get("recorded_at"),
            area=point.get("area"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "area": loc.get("area"), "recorded_at": loc.get("recorded_at")}
