"""MCP transaction attachments — persist Telegram files the way the web UI does."""
import base64
import uuid
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import mcp_server.tools  # noqa: F401
from mcp_server.auth import CallContext
from mcp_server.registry import REGISTRY

pytestmark = pytest.mark.asyncio

STORAGE_PATCH = "app.services.attachment_service.get_storage_provider"

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
    b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
    b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


@dataclass
class FakeStoredFile:
    storage_key: str
    size: int
    content_type: str


def _mock_storage():
    mock = AsyncMock()
    mock.name = "mock"
    mock.upload.side_effect = lambda key, data, ct: FakeStoredFile(
        storage_key=key, size=len(data), content_type=ct
    )
    mock.download.return_value = TINY_PNG
    mock.delete.return_value = None
    return mock


async def test_attach_file_from_path_and_list(session: AsyncSession, test_user, test_transactions, tmp_path: Path):
    tx = test_transactions[0]
    pdf = tmp_path / "flight-ticket.pdf"
    pdf.write_bytes(b"%PDF-1.4 ticket")
    ctx = CallContext(user_id=test_user.id, external=True)
    attach = REGISTRY["propose_attach_file"].handler
    listed = REGISTRY["list_transaction_attachments"].handler

    preview = await attach(session=session, ctx=ctx, transaction_id=str(tx.id), file_path=str(pdf))
    assert preview["kind"] == "attach_file"
    assert "applied" not in preview

    with patch(STORAGE_PATCH, return_value=_mock_storage()):
        applied = await attach(
            session=session,
            ctx=ctx,
            transaction_id=str(tx.id),
            file_path=str(pdf),
            apply=True,
        )
    assert applied.get("applied") is True
    assert applied["attachment"]["filename"] == "flight-ticket.pdf"

    rows = await listed(session=session, ctx=ctx, transaction_id=str(tx.id))
    assert rows["count"] == 1
    assert rows["items"][0]["filename"] == "flight-ticket.pdf"

    got = await REGISTRY["get_transaction"].handler(
        session=session, ctx=ctx, transaction_id=str(tx.id)
    )
    assert got["attachment_count"] == 1
    assert got["attachments"][0]["filename"] == "flight-ticket.pdf"


async def test_attach_file_from_base64_then_delete(session: AsyncSession, test_user, test_transactions):
    tx = test_transactions[0]
    ctx = CallContext(user_id=test_user.id, external=True)
    attach = REGISTRY["propose_attach_file"].handler
    delete = REGISTRY["propose_delete_attachment"].handler

    with patch(STORAGE_PATCH, return_value=_mock_storage()):
        applied = await attach(
            session=session,
            ctx=ctx,
            transaction_id=str(tx.id),
            file_base64=base64.b64encode(TINY_PNG).decode(),
            filename="receipt.png",
            apply=True,
        )
        assert applied.get("applied") is True
        aid = applied["attachment"]["id"]
        removed = await delete(session=session, ctx=ctx, attachment_id=aid, apply=True)
    assert removed.get("deleted") is True
    rows = await REGISTRY["list_transaction_attachments"].handler(
        session=session, ctx=ctx, transaction_id=str(tx.id)
    )
    assert rows["count"] == 0


async def test_attach_file_rejects_unknown_transaction(session: AsyncSession, test_user, tmp_path: Path):
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    ctx = CallContext(user_id=test_user.id, external=True)
    with patch(STORAGE_PATCH, return_value=_mock_storage()):
        r = await REGISTRY["propose_attach_file"].handler(
            session=session,
            ctx=ctx,
            transaction_id=str(uuid.uuid4()),
            file_path=str(pdf),
            apply=True,
        )
    assert r["error"] == "transaction not found"
