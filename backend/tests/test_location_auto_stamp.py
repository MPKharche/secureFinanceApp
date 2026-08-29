"""Last-known location ingest, reverse-geocode labels, auto-stamp on create."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import mcp_server.tools  # noqa: F401
from app.core.config import get_settings
from app.models.user import User
from app.services import location_service, transaction_service
from app.schemas.transaction import TransactionCreate
from mcp_server.auth import CallContext
from mcp_server.registry import REGISTRY

pytestmark = pytest.mark.asyncio


def test_stamp_notes_idempotent():
    loc = {"area": "Kothrud, Pune", "lat": 18.5, "lon": 73.8}
    once = location_service.stamp_notes(None, loc)
    assert once.startswith("📍 Kothrud, Pune")
    assert "#loc-kothrud-pune" in once
    twice = location_service.stamp_notes(once, loc)
    assert twice == once


def test_stamp_notes_keeps_existing_text():
    loc = {"area": "HSR Layout, Bengaluru"}
    out = location_service.stamp_notes("Rapido to office", loc)
    assert out.startswith("Rapido to office")
    assert "📍 HSR Layout, Bengaluru" in out


def test_format_area_prefers_suburb_city():
    assert (
        location_service.format_area({"suburb": "Kothrud", "city": "Pune", "state": "Maharashtra"})
        == "Kothrud, Pune"
    )


async def test_record_and_get_last_location_fresh(
    session: AsyncSession, test_user: User, monkeypatch
):
    monkeypatch.setattr(get_settings(), "location_max_age_minutes", 240)
    with patch.object(
        location_service, "reverse_geocode", new=AsyncMock(return_value="Kothrud, Pune")
    ):
        stored = await location_service.record_location(
            session, test_user.id, 18.5074, 73.8077, accuracy_m=18, source="owntracks"
        )
    assert stored["area"] == "Kothrud, Pune"
    got = await location_service.get_last_location(session, test_user.id)
    assert got is not None
    assert got["area"] == "Kothrud, Pune"
    assert got["stale"] is False
    assert got["age_minutes"] == 0


async def test_stale_location_not_returned(session: AsyncSession, test_user: User, monkeypatch):
    monkeypatch.setattr(get_settings(), "location_max_age_minutes", 60)
    old = datetime.now(timezone.utc) - timedelta(hours=5)
    with patch.object(location_service, "reverse_geocode", new=AsyncMock(return_value="Kothrud, Pune")):
        await location_service.record_location(
            session, test_user.id, 18.5, 73.8, recorded_at=old, area="Kothrud, Pune"
        )
    assert await location_service.get_last_location(session, test_user.id) is None


async def test_create_transaction_auto_stamps_fresh_location(
    session: AsyncSession, test_user: User, test_account, test_workspace, monkeypatch
):
    monkeypatch.setattr(get_settings(), "location_auto_stamp", True)
    with patch.object(location_service, "reverse_geocode", new=AsyncMock(return_value="Kothrud, Pune")):
        await location_service.record_location(
            session, test_user.id, 18.5074, 73.8077, area="Kothrud, Pune"
        )
    tx = await transaction_service.create_transaction(
        session,
        test_workspace.id,
        test_user.id,
        TransactionCreate(
            description="Rapido",
            amount=65,
            date=datetime.now(timezone.utc).date(),
            type="debit",
            account_id=test_account.id,
        ),
    )
    assert tx.notes is not None
    assert "📍 Kothrud, Pune" in tx.notes
    assert "#loc-kothrud-pune" in tx.notes


async def test_create_transaction_skips_stamp_when_notes_already_located(
    session: AsyncSession, test_user: User, test_account, test_workspace
):
    with patch.object(location_service, "reverse_geocode", new=AsyncMock(return_value="Kothrud, Pune")):
        await location_service.record_location(
            session, test_user.id, 18.5, 73.8, area="Kothrud, Pune"
        )
    tx = await transaction_service.create_transaction(
        session,
        test_workspace.id,
        test_user.id,
        TransactionCreate(
            description="Rapido",
            amount=50,
            date=datetime.now(timezone.utc).date(),
            type="debit",
            account_id=test_account.id,
            notes="already 📍 home",
        ),
    )
    assert tx.notes == "already 📍 home"


async def test_propose_create_transaction_preview_includes_location(
    session: AsyncSession, test_user: User, test_account
):
    with patch.object(location_service, "reverse_geocode", new=AsyncMock(return_value="Kothrud, Pune")):
        await location_service.record_location(
            session, test_user.id, 18.5, 73.8, area="Kothrud, Pune"
        )
    handler = REGISTRY["propose_create_transaction"].handler
    ctx = CallContext(user_id=test_user.id, external=True)
    result = await handler(
        session=session,
        ctx=ctx,
        description="Rapido",
        amount=65,
        type="debit",
        account_id=str(test_account.id),
    )
    assert result["kind"] == "create_transaction"
    assert result["location"]["area"] == "Kothrud, Pune"
    assert "📍 Kothrud, Pune" in (result["proposed"]["notes"] or "")


async def test_mcp_record_and_get_last_location(session: AsyncSession, test_user: User):
    ctx = CallContext(user_id=test_user.id, external=True)
    with patch.object(location_service, "reverse_geocode", new=AsyncMock(return_value="Indiranagar, Bengaluru")):
        written = await REGISTRY["record_location"].handler(
            session=session, ctx=ctx, latitude=12.9716, longitude=77.6412
        )
    assert written.get("ok") is True
    got = await REGISTRY["get_last_location"].handler(session=session, ctx=ctx)
    assert got["fresh"] is True
    assert got["location"]["area"] == "Indiranagar, Bengaluru"


async def test_ingest_requires_token(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "location_ingest_token", "secret-token")
    monkeypatch.setattr(get_settings(), "location_ingest_user_id", str(uuid.uuid4()))
    r = await client.post("/api/location/owntracks", json={"lat": 18.5, "lon": 73.8})
    assert r.status_code == 401


async def test_ingest_owntracks_accepts_http_basic(
    client, test_user: User, monkeypatch
):
    monkeypatch.setattr(get_settings(), "location_ingest_token", "secret-token")
    monkeypatch.setattr(get_settings(), "location_ingest_user_id", str(test_user.id))
    with patch.object(location_service, "reverse_geocode", new=AsyncMock(return_value="Kothrud, Pune")):
        r = await client.post(
            "/api/location/owntracks",
            json={"_type": "location", "lat": 18.5074, "lon": 73.8077},
            auth=("mayur", "secret-token"),
        )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


async def test_ingest_owntracks_stores_location(
    client, test_user: User, monkeypatch
):
    monkeypatch.setattr(get_settings(), "location_ingest_token", "secret-token")
    monkeypatch.setattr(get_settings(), "location_ingest_user_id", str(test_user.id))
    with patch.object(location_service, "reverse_geocode", new=AsyncMock(return_value="Kothrud, Pune")):
        r = await client.post(
            "/api/location/owntracks",
            json={
                "_type": "location",
                "lat": 18.5074,
                "lon": 73.8077,
                "acc": 12,
                "tst": datetime.now(timezone.utc).timestamp(),
            },
            headers={"Authorization": "Bearer secret-token"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["area"] == "Kothrud, Pune"
