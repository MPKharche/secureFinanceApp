"""Transaction attachments — same store the web app uses.

Telegram (and other MCP clients) send a local path or base64. We persist
via `attachment_service` so the paperclip on money.planetfinance.cloud
shows the file. Never tell the user to upload it in the browser.
"""
from __future__ import annotations

import base64
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import attachment_service
from mcp_server.auth import CallContext
from mcp_server.registry import tool
from mcp_server.tools._helpers import parse_uuid, resolve_workspace_id
from mcp_server.tools.proposals import _APPLY_FIELD, _PROPOSAL_PREFACE, _can_apply

_HOST_PROFILE = Path("/root/apps/hermes-agent/data/profiles/securo")
_CONTAINER_PROFILE = Path(os.environ.get("HERMES_MEDIA_ROOT", "/hermes-profile"))
_ALLOWED_ROOTS = (
    _CONTAINER_PROFILE / "cache",
    _CONTAINER_PROFILE / "image_cache",
    _HOST_PROFILE / "cache",
    _HOST_PROFILE / "image_cache",
    Path(tempfile.gettempdir()),
    Path("/tmp"),
    Path("/var/tmp"),
)


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _resolve_readable_file(raw: str) -> Path:
    """Map a Hermes 'saved at:' path onto a file MCP can actually read."""
    given = Path(raw).expanduser()
    candidates: list[Path] = [given]
    try:
        rel = given.resolve(strict=False).relative_to(_HOST_PROFILE)
        candidates.append(_CONTAINER_PROFILE / rel)
    except ValueError:
        pass
    if str(given).startswith("/hermes-profile"):
        candidates.append(given)

    for cand in candidates:
        try:
            resolved = cand.resolve(strict=True)
        except OSError:
            continue
        if not resolved.is_file():
            continue
        if not any(_is_under(resolved, root) for root in _ALLOWED_ROOTS):
            continue
        return resolved
    raise FileNotFoundError(
        "file not readable from MCP (pass the Telegram 'saved at' path, "
        "or file_base64). Allowed: hermes profile cache / /tmp."
    )


def _meta(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "transaction_id": str(row.transaction_id),
        "filename": row.filename,
        "content_type": row.content_type,
        "size": int(row.size),
        "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
    }


def _bytes_from_args(
    *,
    file_path: str | None,
    file_base64: str | None,
    filename: str | None,
) -> tuple[str, str, bytes]:
    if bool(file_path) == bool(file_base64):
        raise ValueError("pass exactly one of file_path or file_base64")
    if file_path:
        path = _resolve_readable_file(file_path)
        data = path.read_bytes()
        name = filename or path.name
    else:
        try:
            data = base64.b64decode(file_base64 or "", validate=False)
        except Exception as exc:
            raise ValueError(f"invalid file_base64: {exc}") from exc
        name = filename or "attachment.bin"
    if not data:
        raise ValueError("empty file")
    content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    return name, content_type, data


@tool(
    name="list_transaction_attachments",
    description=(
        "List files attached to a booked transaction (receipts, tickets, "
        "PDFs, photos). Same records the web paperclip shows. Use this "
        "before delete/rename. Do not send the user to the web app."
    ),
    parameters={
        "type": "object",
        "properties": {
            "transaction_id": {"type": "string", "format": "uuid"},
        },
        "required": ["transaction_id"],
        "additionalProperties": False,
    },
    tags=["read", "transactions", "attachments"],
)
async def list_transaction_attachments(
    *,
    session: AsyncSession,
    ctx: CallContext,
    transaction_id: str,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    tid = parse_uuid(transaction_id)
    if tid is None:
        return {"error": "invalid transaction id"}
    try:
        rows = await attachment_service.list_attachments(session, ws_id, tid)
    except LookupError:
        return {"error": "transaction not found"}
    return {"transaction_id": str(tid), "count": len(rows), "items": [_meta(r) for r in rows]}


@tool(
    name="propose_attach_file",
    description=_PROPOSAL_PREFACE
    + (
        "Attach a receipt, ticket PDF, or photo to an already-booked "
        "transaction. This is the Telegram equivalent of the web upload. "
        "Pass file_path from the system note 'saved at: …' (Hermes cache), "
        "or file_base64 plus filename. Allowed: jpg,jpeg,png,webp,gif,heic,pdf "
        "up to 10 MB, max 10 files per transaction. For this user call with "
        "apply=true. Never tell them to upload it on the website."
    ),
    parameters={
        "type": "object",
        "properties": {
            "transaction_id": {"type": "string", "format": "uuid"},
            "file_path": {
                "type": "string",
                "description": "Absolute path from Telegram/Hermes 'saved at:'. Preferred.",
            },
            "file_base64": {
                "type": "string",
                "description": "Raw file bytes as base64 if no readable path.",
            },
            "filename": {
                "type": "string",
                "description": "Original name including extension, e.g. ticket.pdf",
            },
            "apply": _APPLY_FIELD,
        },
        "required": ["transaction_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "transactions", "attachments"],
)
async def propose_attach_file(
    *,
    session: AsyncSession,
    ctx: CallContext,
    transaction_id: str,
    file_path: str | None = None,
    file_base64: str | None = None,
    filename: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    tid = parse_uuid(transaction_id)
    if tid is None:
        return {"error": "invalid transaction id"}
    try:
        name, content_type, data = _bytes_from_args(
            file_path=file_path, file_base64=file_base64, filename=filename
        )
    except (ValueError, FileNotFoundError) as exc:
        return {"error": str(exc)}

    preview = {
        "kind": "attach_file",
        "transaction_id": str(tid),
        "filename": name,
        "content_type": content_type,
        "size": len(data),
    }
    if not _can_apply(ctx, apply):
        return preview
    try:
        row = await attachment_service.upload_attachment(
            session=session,
            workspace_id=ws_id,
            user_id=ctx.user_id,
            transaction_id=tid,
            filename=name,
            content_type=content_type,
            data=data,
        )
    except LookupError:
        return {"error": "transaction not found"}
    except ValueError as exc:
        return {"error": str(exc)}
    return {**preview, "applied": True, "attachment": _meta(row)}


@tool(
    name="propose_rename_attachment",
    description=_PROPOSAL_PREFACE
    + "Rename a file already attached to a transaction. apply=true for this user.",
    parameters={
        "type": "object",
        "properties": {
            "attachment_id": {"type": "string", "format": "uuid"},
            "filename": {"type": "string", "minLength": 1, "maxLength": 200},
            "apply": _APPLY_FIELD,
        },
        "required": ["attachment_id", "filename"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "transactions", "attachments"],
)
async def propose_rename_attachment(
    *,
    session: AsyncSession,
    ctx: CallContext,
    attachment_id: str,
    filename: str,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    aid = parse_uuid(attachment_id)
    if aid is None:
        return {"error": "invalid attachment id"}
    preview = {"kind": "rename_attachment", "attachment_id": str(aid), "filename": filename}
    if not _can_apply(ctx, apply):
        return preview
    try:
        row = await attachment_service.rename_attachment(session, aid, ws_id, filename)
    except LookupError:
        return {"error": "attachment not found"}
    except ValueError as exc:
        return {"error": str(exc)}
    return {**preview, "applied": True, "attachment": _meta(row)}


@tool(
    name="propose_delete_attachment",
    description=_PROPOSAL_PREFACE
    + "Remove a file from a transaction (DB + storage). apply=true for this user.",
    parameters={
        "type": "object",
        "properties": {
            "attachment_id": {"type": "string", "format": "uuid"},
            "apply": _APPLY_FIELD,
        },
        "required": ["attachment_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "transactions", "attachments"],
)
async def propose_delete_attachment(
    *,
    session: AsyncSession,
    ctx: CallContext,
    attachment_id: str,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    aid = parse_uuid(attachment_id)
    if aid is None:
        return {"error": "invalid attachment id"}
    preview = {"kind": "delete_attachment", "attachment_id": str(aid)}
    if not _can_apply(ctx, apply):
        return preview
    try:
        await attachment_service.delete_attachment(session, aid, ws_id)
    except LookupError:
        return {"error": "attachment not found"}
    return {**preview, "applied": True, "deleted": True}
