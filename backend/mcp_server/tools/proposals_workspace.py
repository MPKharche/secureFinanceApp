"""User-level money mutations that were previously web-app-only.

Accounts, transfers, payees, category edits, budget/goal adjustments,
assets, expense groups, and settlements. Same preview-then-apply gate as
`proposals.py`: internal Securo UI never writes; external clients
(Finance Orbit) pass apply=true after the user confirms.
"""

from __future__ import annotations

from datetime import date as date_cls
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace
from app.schemas.account import AccountCreate, AccountUpdate
from app.schemas.asset import (
    AssetCreate,
    AssetTransactionCreate,
    AssetUpdate,
    AssetValueCreate,
)
from app.schemas.budget import BudgetUpdate
from app.schemas.category import CategoryUpdate
from app.schemas.goal import GoalUpdate
from app.schemas.group import GroupCreate, GroupMemberCreate
from app.schemas.group_settlement import GroupSettlementCreate
from app.schemas.payee import PayeeCreate, PayeeUpdate
from app.schemas.transaction import TransferCreate
from app.services import (
    account_service,
    asset_service,
    asset_transaction_service,
    budget_service,
    category_service,
    goal_service,
    group_service,
    payee_service,
    settlement_service,
    transaction_service,
)
from mcp_server.auth import CallContext
from mcp_server.registry import tool
from mcp_server.tools._helpers import num, parse_date, parse_uuid, resolve_workspace_id
from mcp_server.tools.proposals import _APPLY_FIELD, _PROPOSAL_PREFACE, _can_apply


async def _default_currency(session: AsyncSession, ws_id) -> str:
    ws = await session.get(Workspace, ws_id)
    return (getattr(ws, "default_currency", None) or "INR").upper()


def _err(msg: str) -> dict[str, Any]:
    return {"error": msg}


# --- Accounts --------------------------------------------------------------


@tool(
    name="propose_create_account",
    description=_PROPOSAL_PREFACE
    + (
        "Preview creating a manual account (checking, savings, credit card, "
        "wallet, etc.). Use this instead of sending the user to the web app. "
        "Bank-sync connections stay in the web app. Currency defaults to the "
        "workspace currency. Opening balance 0 unless the user gives one."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 255},
            "account_type": {
                "type": "string",
                "enum": [
                    "checking",
                    "savings",
                    "credit_card",
                    "wallet",
                    "investment",
                    "loan",
                    "other",
                ],
            },
            "currency": {"type": "string"},
            "balance": {"type": "number", "description": "Opening balance; default 0"},
            "credit_limit": {"type": "number"},
            "apply": _APPLY_FIELD,
        },
        "required": ["name", "account_type"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "accounts"],
)
async def propose_create_account(
    *,
    session: AsyncSession,
    ctx: CallContext,
    name: str,
    account_type: str,
    currency: str | None = None,
    balance: float | None = None,
    credit_limit: float | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    resolved = (currency or await _default_currency(session, ws_id)).upper()
    opening = float(balance) if balance is not None else 0.0
    proposed = {
        "name": name.strip(),
        "type": account_type,
        "currency": resolved,
        "balance": opening,
        "credit_limit": float(credit_limit) if credit_limit is not None else None,
    }
    preview = {
        "kind": "create_account",
        "proposed": proposed,
        "apply_endpoint": "POST /api/accounts",
    }
    if _can_apply(ctx, apply):
        created = await account_service.create_account(
            session,
            ws_id,
            ctx.user_id,
            AccountCreate(
                name=proposed["name"],
                type=account_type,
                currency=resolved,
                balance=Decimal(str(opening)),
                credit_limit=Decimal(str(credit_limit)) if credit_limit is not None else None,
            ),
        )
        return {**preview, "applied": True, "id": str(created.id)}
    return preview


@tool(
    name="propose_update_account",
    description=_PROPOSAL_PREFACE
    + (
        "Preview editing an account. Manual accounts: name, type, opening "
        "balance, credit-card metadata. Synced bank accounts: only "
        "display_name (nickname), type, and card metadata — not the "
        "provider name or synced balance."
    ),
    parameters={
        "type": "object",
        "properties": {
            "account_id": {"type": "string", "format": "uuid"},
            "name": {"type": "string", "minLength": 1, "maxLength": 255},
            "display_name": {"type": "string", "maxLength": 255},
            "account_type": {
                "type": "string",
                "enum": [
                    "checking",
                    "savings",
                    "credit_card",
                    "wallet",
                    "investment",
                    "loan",
                    "other",
                ],
            },
            "balance": {"type": "number"},
            "credit_limit": {"type": "number"},
            "apply": _APPLY_FIELD,
        },
        "required": ["account_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "accounts"],
)
async def propose_update_account(
    *,
    session: AsyncSession,
    ctx: CallContext,
    account_id: str,
    name: str | None = None,
    display_name: str | None = None,
    account_type: str | None = None,
    balance: float | None = None,
    credit_limit: float | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    acc = await account_service.get_account(session, parse_uuid(account_id), ws_id)
    if acc is None:
        return _err("account not found")
    update_data: dict[str, Any] = {}
    changes: dict[str, Any] = {}
    if name is not None:
        update_data["name"] = name.strip()
        changes["name"] = name.strip()
    if display_name is not None:
        update_data["display_name"] = display_name.strip() or None
        changes["display_name"] = display_name.strip() or None
    if account_type is not None:
        update_data["type"] = account_type
        changes["type"] = account_type
    if balance is not None:
        update_data["balance"] = Decimal(str(balance))
        changes["balance"] = float(balance)
    if credit_limit is not None:
        update_data["credit_limit"] = Decimal(str(credit_limit))
        changes["credit_limit"] = float(credit_limit)
    if not changes:
        return _err("no changes provided")
    preview = {
        "kind": "update_account",
        "target": {
            "id": str(acc.id),
            "name": acc.name,
            "display_name": acc.display_name,
            "type": acc.type,
            "currency": acc.currency,
            "is_closed": bool(acc.is_closed),
            "synced": acc.connection_id is not None,
        },
        "changes": changes,
        "apply_endpoint": f"PATCH /api/accounts/{acc.id}",
    }
    if _can_apply(ctx, apply):
        try:
            updated = await account_service.update_account(
                session, acc.id, ws_id, AccountUpdate(**update_data)
            )
        except ValueError as exc:
            return {**preview, "error": str(exc)}
        if updated is None:
            return {**preview, "error": "account not found"}
        return {**preview, "applied": True, "id": str(updated.id)}
    return preview


@tool(
    name="propose_close_account",
    description=_PROPOSAL_PREFACE
    + (
        "Preview closing, reopening, or deleting an account. close = hide "
        "from lists but keep history (works for synced too). reopen = undo "
        "close. delete = remove a *manual* account only — synced bank "
        "accounts cannot be deleted here (close them instead)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "account_id": {"type": "string", "format": "uuid"},
            "mode": {
                "type": "string",
                "enum": ["close", "reopen", "delete"],
                "default": "close",
            },
            "apply": _APPLY_FIELD,
        },
        "required": ["account_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "accounts"],
)
async def propose_close_account(
    *,
    session: AsyncSession,
    ctx: CallContext,
    account_id: str,
    mode: str = "close",
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    acc = await account_service.get_account(session, parse_uuid(account_id), ws_id)
    if acc is None:
        return _err("account not found")
    preview = {
        "kind": "close_account",
        "mode": mode,
        "target": {
            "id": str(acc.id),
            "name": acc.name,
            "type": acc.type,
            "is_closed": bool(acc.is_closed),
            "synced": acc.connection_id is not None,
        },
        "apply_endpoint": f"POST /api/accounts/{acc.id}/{mode}",
    }
    if _can_apply(ctx, apply):
        try:
            if mode == "delete":
                ok = await account_service.delete_account(session, acc.id, ws_id)
                if not ok:
                    return {**preview, "error": "account not found"}
                return {**preview, "applied": True, "deleted": True}
            if mode == "reopen":
                updated = await account_service.reopen_account(session, acc.id, ws_id)
            else:
                updated = await account_service.close_account(session, acc.id, ws_id)
        except ValueError as exc:
            return {**preview, "error": str(exc)}
        if updated is None:
            return {**preview, "error": "account not found"}
        return {**preview, "applied": True, "id": str(updated.id), "is_closed": bool(updated.is_closed)}
    return preview


# --- Transfers -------------------------------------------------------------


@tool(
    name="propose_create_transfer",
    description=_PROPOSAL_PREFACE
    + (
        "Preview a transfer between two of the user's accounts (e.g. wallet "
        "to ICICI Bank). Creates the paired debit+credit. Not a bank "
        "payment to someone else — that is a normal expense transaction."
    ),
    parameters={
        "type": "object",
        "properties": {
            "from_account_id": {"type": "string", "format": "uuid"},
            "to_account_id": {"type": "string", "format": "uuid"},
            "amount": {"type": "number", "exclusiveMinimum": 0},
            "date": {"type": "string", "format": "date", "description": "Defaults to today"},
            "description": {"type": "string"},
            "notes": {"type": "string"},
            "destination_amount": {
                "type": "number",
                "exclusiveMinimum": 0,
                "description": "Required only for cross-currency transfers",
            },
            "apply": _APPLY_FIELD,
        },
        "required": ["from_account_id", "to_account_id", "amount"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "transfers"],
)
async def propose_create_transfer(
    *,
    session: AsyncSession,
    ctx: CallContext,
    from_account_id: str,
    to_account_id: str,
    amount: float,
    date: str | None = None,
    description: str | None = None,
    notes: str | None = None,
    destination_amount: float | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    src = await account_service.get_account(session, parse_uuid(from_account_id), ws_id)
    dst = await account_service.get_account(session, parse_uuid(to_account_id), ws_id)
    if src is None:
        return _err("source account not found")
    if dst is None:
        return _err("destination account not found")
    target_date = parse_date(date) or date_cls.today()
    desc = (description or f"Transfer {src.name} → {dst.name}").strip()
    proposed = {
        "from_account_id": str(src.id),
        "from_account_name": src.name,
        "to_account_id": str(dst.id),
        "to_account_name": dst.name,
        "amount": float(amount),
        "currency": src.currency,
        "destination_amount": float(destination_amount) if destination_amount is not None else None,
        "date": target_date.isoformat(),
        "description": desc,
        "notes": notes,
    }
    preview = {
        "kind": "create_transfer",
        "proposed": proposed,
        "apply_endpoint": "POST /api/transactions/transfer",
    }
    if _can_apply(ctx, apply):
        try:
            debit, credit = await transaction_service.create_transfer(
                session,
                ws_id,
                ctx.user_id,
                TransferCreate(
                    from_account_id=src.id,
                    to_account_id=dst.id,
                    amount=Decimal(str(amount)),
                    destination_amount=(
                        Decimal(str(destination_amount)) if destination_amount is not None else None
                    ),
                    date=target_date,
                    description=desc,
                    notes=notes,
                ),
            )
        except ValueError as exc:
            return {**preview, "error": str(exc)}
        return {
            **preview,
            "applied": True,
            "debit_id": str(debit.id),
            "credit_id": str(credit.id),
            "transfer_pair_id": str(debit.transfer_pair_id),
        }
    return preview


# --- Payees ----------------------------------------------------------------


@tool(
    name="propose_create_payee",
    description=_PROPOSAL_PREFACE
    + "Preview adding a merchant/payee (e.g. 'add Swiggy as a payee').",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 255},
            "payee_type": {"type": "string", "enum": ["person", "company"]},
            "notes": {"type": "string"},
            "apply": _APPLY_FIELD,
        },
        "required": ["name"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "payees"],
)
async def propose_create_payee(
    *,
    session: AsyncSession,
    ctx: CallContext,
    name: str,
    payee_type: str | None = None,
    notes: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    proposed = {"name": name.strip(), "type": payee_type, "notes": notes}
    preview = {"kind": "create_payee", "proposed": proposed, "apply_endpoint": "POST /api/payees"}
    if _can_apply(ctx, apply):
        created = await payee_service.create_payee(
            session,
            ws_id,
            ctx.user_id,
            PayeeCreate(name=proposed["name"], type=payee_type, notes=notes),
        )
        return {**preview, "applied": True, "id": str(created.id)}
    return preview


@tool(
    name="propose_update_payee",
    description=_PROPOSAL_PREFACE
    + "Preview renaming or editing a payee. Pass payee_id from list_payees.",
    parameters={
        "type": "object",
        "properties": {
            "payee_id": {"type": "string", "format": "uuid"},
            "name": {"type": "string", "minLength": 1, "maxLength": 255},
            "payee_type": {"type": "string", "enum": ["person", "company"]},
            "notes": {"type": "string"},
            "is_favorite": {"type": "boolean"},
            "apply": _APPLY_FIELD,
        },
        "required": ["payee_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "payees"],
)
async def propose_update_payee(
    *,
    session: AsyncSession,
    ctx: CallContext,
    payee_id: str,
    name: str | None = None,
    payee_type: str | None = None,
    notes: str | None = None,
    is_favorite: bool | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    payee = await payee_service.get_payee(session, parse_uuid(payee_id), ws_id)
    if payee is None:
        return _err("payee not found")
    update_data: dict[str, Any] = {}
    changes: dict[str, Any] = {}
    if name is not None:
        update_data["name"] = name.strip()
        changes["name"] = name.strip()
    if payee_type is not None:
        update_data["type"] = payee_type
        changes["type"] = payee_type
    if notes is not None:
        update_data["notes"] = notes
        changes["notes"] = notes
    if is_favorite is not None:
        update_data["is_favorite"] = bool(is_favorite)
        changes["is_favorite"] = bool(is_favorite)
    if not changes:
        return _err("no changes provided")
    preview = {
        "kind": "update_payee",
        "target": {"id": str(payee.id), "name": payee.name, "type": payee.type},
        "changes": changes,
        "apply_endpoint": f"PATCH /api/payees/{payee.id}",
    }
    if _can_apply(ctx, apply):
        updated = await payee_service.update_payee(
            session, payee.id, ws_id, PayeeUpdate(**update_data)
        )
        if updated is None:
            return {**preview, "error": "payee not found"}
        return {**preview, "applied": True, "id": str(updated.id)}
    return preview


@tool(
    name="propose_delete_payee",
    description=_PROPOSAL_PREFACE + "Preview deleting a payee. Transactions keep their history.",
    parameters={
        "type": "object",
        "properties": {
            "payee_id": {"type": "string", "format": "uuid"},
            "apply": _APPLY_FIELD,
        },
        "required": ["payee_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "payees"],
)
async def propose_delete_payee(
    *,
    session: AsyncSession,
    ctx: CallContext,
    payee_id: str,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    payee = await payee_service.get_payee(session, parse_uuid(payee_id), ws_id)
    if payee is None:
        return _err("payee not found")
    preview = {
        "kind": "delete_payee",
        "target": {"id": str(payee.id), "name": payee.name},
        "apply_endpoint": f"DELETE /api/payees/{payee.id}",
    }
    if _can_apply(ctx, apply):
        ok = await payee_service.delete_payee(session, payee.id, ws_id)
        if not ok:
            return {**preview, "error": "payee not found"}
        return {**preview, "applied": True, "deleted": True}
    return preview


# --- Categories ------------------------------------------------------------


@tool(
    name="propose_update_category",
    description=_PROPOSAL_PREFACE
    + "Preview renaming/hiding a category. Use list_categories first.",
    parameters={
        "type": "object",
        "properties": {
            "category_id": {"type": "string", "format": "uuid"},
            "name": {"type": "string", "minLength": 1, "maxLength": 100},
            "icon": {"type": "string"},
            "color": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
            "is_hidden": {"type": "boolean"},
            "is_ignored": {"type": "boolean"},
            "apply": _APPLY_FIELD,
        },
        "required": ["category_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "categories"],
)
async def propose_update_category(
    *,
    session: AsyncSession,
    ctx: CallContext,
    category_id: str,
    name: str | None = None,
    icon: str | None = None,
    color: str | None = None,
    is_hidden: bool | None = None,
    is_ignored: bool | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    cat = await category_service.get_category(session, parse_uuid(category_id), ws_id)
    if cat is None:
        return _err("category not found")
    update_data: dict[str, Any] = {}
    changes: dict[str, Any] = {}
    if name is not None:
        update_data["name"] = name.strip()
        changes["name"] = name.strip()
    if icon is not None:
        update_data["icon"] = icon
        changes["icon"] = icon
    if color is not None:
        update_data["color"] = color
        changes["color"] = color
    if is_hidden is not None:
        update_data["is_hidden"] = bool(is_hidden)
        changes["is_hidden"] = bool(is_hidden)
    if is_ignored is not None:
        update_data["is_ignored"] = bool(is_ignored)
        changes["is_ignored"] = bool(is_ignored)
    if not changes:
        return _err("no changes provided")
    preview = {
        "kind": "update_category",
        "target": {"id": str(cat.id), "name": cat.name, "is_system": bool(cat.is_system)},
        "changes": changes,
        "apply_endpoint": f"PATCH /api/categories/{cat.id}",
    }
    if _can_apply(ctx, apply):
        updated = await category_service.update_category(
            session, cat.id, ws_id, CategoryUpdate(**update_data)
        )
        if updated is None:
            return {**preview, "error": "category not found"}
        return {**preview, "applied": True, "id": str(updated.id)}
    return preview


@tool(
    name="propose_delete_category",
    description=_PROPOSAL_PREFACE
    + "Preview deleting a non-system category. Transactions in it become uncategorized.",
    parameters={
        "type": "object",
        "properties": {
            "category_id": {"type": "string", "format": "uuid"},
            "apply": _APPLY_FIELD,
        },
        "required": ["category_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "categories"],
)
async def propose_delete_category(
    *,
    session: AsyncSession,
    ctx: CallContext,
    category_id: str,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    cat = await category_service.get_category(session, parse_uuid(category_id), ws_id)
    if cat is None:
        return _err("category not found")
    preview = {
        "kind": "delete_category",
        "target": {"id": str(cat.id), "name": cat.name, "is_system": bool(cat.is_system)},
        "apply_endpoint": f"DELETE /api/categories/{cat.id}",
    }
    if _can_apply(ctx, apply):
        ok = await category_service.delete_category(session, cat.id, ws_id)
        if not ok:
            return {**preview, "error": "category not found or is a system category"}
        return {**preview, "applied": True, "deleted": True}
    return preview


# --- Budgets ---------------------------------------------------------------


@tool(
    name="propose_update_budget",
    description=_PROPOSAL_PREFACE
    + "Preview changing a monthly budget amount. Pass budget_id from list_budgets.",
    parameters={
        "type": "object",
        "properties": {
            "budget_id": {"type": "string", "format": "uuid"},
            "amount": {"type": "number", "exclusiveMinimum": 0},
            "apply": _APPLY_FIELD,
        },
        "required": ["budget_id", "amount"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "budgets"],
)
async def propose_update_budget(
    *,
    session: AsyncSession,
    ctx: CallContext,
    budget_id: str,
    amount: float,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    budget = await budget_service.get_budget(session, parse_uuid(budget_id), ws_id)
    if budget is None:
        return _err("budget not found")
    preview = {
        "kind": "update_budget",
        "target": {
            "id": str(budget.id),
            "category_id": str(budget.category_id),
            "amount": num(budget.amount),
            "month": budget.month.isoformat() if budget.month else None,
        },
        "changes": {"amount": float(amount)},
        "apply_endpoint": f"PATCH /api/budgets/{budget.id}",
    }
    if _can_apply(ctx, apply):
        updated = await budget_service.update_budget(
            session, budget.id, ws_id, BudgetUpdate(amount=Decimal(str(amount)))
        )
        if updated is None:
            return {**preview, "error": "budget not found"}
        return {**preview, "applied": True, "id": str(updated.id)}
    return preview


@tool(
    name="propose_delete_budget",
    description=_PROPOSAL_PREFACE + "Preview deleting a budget row.",
    parameters={
        "type": "object",
        "properties": {
            "budget_id": {"type": "string", "format": "uuid"},
            "apply": _APPLY_FIELD,
        },
        "required": ["budget_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "budgets"],
)
async def propose_delete_budget(
    *,
    session: AsyncSession,
    ctx: CallContext,
    budget_id: str,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    budget = await budget_service.get_budget(session, parse_uuid(budget_id), ws_id)
    if budget is None:
        return _err("budget not found")
    preview = {
        "kind": "delete_budget",
        "target": {"id": str(budget.id), "amount": num(budget.amount)},
        "apply_endpoint": f"DELETE /api/budgets/{budget.id}",
    }
    if _can_apply(ctx, apply):
        ok = await budget_service.delete_budget(session, budget.id, ws_id)
        if not ok:
            return {**preview, "error": "budget not found"}
        return {**preview, "applied": True, "deleted": True}
    return preview


# --- Goals -----------------------------------------------------------------


@tool(
    name="propose_update_goal",
    description=_PROPOSAL_PREFACE
    + (
        "Preview editing a savings goal. current_amount is the new total "
        "saved (absolute). add_amount adds to the current total (use this "
        "for 'I put ₹500 toward vacation'). status: active/completed/"
        "paused/archived."
    ),
    parameters={
        "type": "object",
        "properties": {
            "goal_id": {"type": "string", "format": "uuid"},
            "name": {"type": "string", "minLength": 1},
            "target_amount": {"type": "number", "exclusiveMinimum": 0},
            "current_amount": {"type": "number", "minimum": 0},
            "add_amount": {
                "type": "number",
                "description": "Increment saved amount (not a replacement)",
            },
            "deadline": {"type": "string", "format": "date"},
            "status": {
                "type": "string",
                "enum": ["active", "completed", "paused", "archived"],
            },
            "apply": _APPLY_FIELD,
        },
        "required": ["goal_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "goals"],
)
async def propose_update_goal(
    *,
    session: AsyncSession,
    ctx: CallContext,
    goal_id: str,
    name: str | None = None,
    target_amount: float | None = None,
    current_amount: float | None = None,
    add_amount: float | None = None,
    deadline: str | None = None,
    status: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    goal = await goal_service.get_goal(session, parse_uuid(goal_id), ws_id, ctx.user_id)
    if goal is None:
        return _err("goal not found")
    update_data: dict[str, Any] = {}
    changes: dict[str, Any] = {}
    if name is not None:
        update_data["name"] = name.strip()
        changes["name"] = name.strip()
    if target_amount is not None:
        update_data["target_amount"] = Decimal(str(target_amount))
        changes["target_amount"] = float(target_amount)
    if current_amount is not None and add_amount is not None:
        return _err("pass current_amount or add_amount, not both")
    if current_amount is not None:
        update_data["current_amount"] = Decimal(str(current_amount))
        changes["current_amount"] = float(current_amount)
    if add_amount is not None:
        new_total = float(goal.current_amount or 0) + float(add_amount)
        update_data["current_amount"] = Decimal(str(new_total))
        changes["current_amount"] = new_total
        changes["add_amount"] = float(add_amount)
    if deadline is not None:
        parsed = parse_date(deadline)
        update_data["target_date"] = parsed
        changes["deadline"] = parsed.isoformat() if parsed else None
    if status is not None:
        update_data["status"] = status
        changes["status"] = status
    if not changes:
        return _err("no changes provided")
    preview = {
        "kind": "update_goal",
        "target": {
            "id": str(goal.id),
            "name": goal.name,
            "target_amount": num(goal.target_amount),
            "current_amount": num(goal.current_amount),
            "status": goal.status,
        },
        "changes": changes,
        "apply_endpoint": f"PATCH /api/goals/{goal.id}",
    }
    if _can_apply(ctx, apply):
        updated = await goal_service.update_goal(
            session, goal.id, ws_id, ctx.user_id, GoalUpdate(**update_data)
        )
        if updated is None:
            return {**preview, "error": "goal not found"}
        return {**preview, "applied": True, "id": str(updated.id)}
    return preview


@tool(
    name="propose_delete_goal",
    description=_PROPOSAL_PREFACE + "Preview deleting a savings goal.",
    parameters={
        "type": "object",
        "properties": {
            "goal_id": {"type": "string", "format": "uuid"},
            "apply": _APPLY_FIELD,
        },
        "required": ["goal_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "goals"],
)
async def propose_delete_goal(
    *,
    session: AsyncSession,
    ctx: CallContext,
    goal_id: str,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    goal = await goal_service.get_goal(session, parse_uuid(goal_id), ws_id, ctx.user_id)
    if goal is None:
        return _err("goal not found")
    preview = {
        "kind": "delete_goal",
        "target": {"id": str(goal.id), "name": goal.name},
        "apply_endpoint": f"DELETE /api/goals/{goal.id}",
    }
    if _can_apply(ctx, apply):
        ok = await goal_service.delete_goal(session, goal.id, ws_id)
        if not ok:
            return {**preview, "error": "goal not found"}
        return {**preview, "applied": True, "deleted": True}
    return preview


# --- Assets ----------------------------------------------------------------


@tool(
    name="propose_create_asset",
    description=_PROPOSAL_PREFACE
    + (
        "Preview adding a holding (property, vehicle, stock/ticker, gold, "
        "etc.). type is real_estate/vehicle/valuable/investment/other. "
        "For a stock/crypto pass ticker. current_value seeds the first "
        "valuation for manual assets."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 255},
            "asset_type": {
                "type": "string",
                "enum": ["real_estate", "vehicle", "valuable", "investment", "other"],
            },
            "currency": {"type": "string"},
            "current_value": {"type": "number", "minimum": 0},
            "ticker": {"type": "string"},
            "units": {"type": "number"},
            "apply": _APPLY_FIELD,
        },
        "required": ["name", "asset_type"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "assets"],
)
async def propose_create_asset(
    *,
    session: AsyncSession,
    ctx: CallContext,
    name: str,
    asset_type: str,
    currency: str | None = None,
    current_value: float | None = None,
    ticker: str | None = None,
    units: float | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    resolved = (currency or await _default_currency(session, ws_id)).upper()
    proposed = {
        "name": name.strip(),
        "type": asset_type,
        "currency": resolved,
        "current_value": float(current_value) if current_value is not None else None,
        "ticker": ticker,
        "units": float(units) if units is not None else None,
    }
    preview = {"kind": "create_asset", "proposed": proposed, "apply_endpoint": "POST /api/assets"}
    if _can_apply(ctx, apply):
        created = await asset_service.create_asset(
            session,
            ws_id,
            ctx.user_id,
            AssetCreate(
                name=proposed["name"],
                type=asset_type,
                currency=resolved,
                current_value=Decimal(str(current_value)) if current_value is not None else None,
                ticker=ticker,
                units=Decimal(str(units)) if units is not None else None,
            ),
        )
        return {**preview, "applied": True, "id": str(created.id)}
    return preview


@tool(
    name="propose_update_asset",
    description=_PROPOSAL_PREFACE
    + (
        "Preview editing a holding. Optional current_value records a new "
        "manual valuation point. is_archived=true hides it from the active list."
    ),
    parameters={
        "type": "object",
        "properties": {
            "asset_id": {"type": "string", "format": "uuid"},
            "name": {"type": "string", "minLength": 1},
            "current_value": {"type": "number", "minimum": 0},
            "value_date": {"type": "string", "format": "date"},
            "is_archived": {"type": "boolean"},
            "apply": _APPLY_FIELD,
        },
        "required": ["asset_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "assets"],
)
async def propose_update_asset(
    *,
    session: AsyncSession,
    ctx: CallContext,
    asset_id: str,
    name: str | None = None,
    current_value: float | None = None,
    value_date: str | None = None,
    is_archived: bool | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    asset = await asset_service.get_asset(session, parse_uuid(asset_id), ws_id)
    if asset is None:
        return _err("asset not found")
    update_data: dict[str, Any] = {}
    changes: dict[str, Any] = {}
    if name is not None:
        update_data["name"] = name.strip()
        changes["name"] = name.strip()
    if is_archived is not None:
        update_data["is_archived"] = bool(is_archived)
        changes["is_archived"] = bool(is_archived)
    if current_value is not None:
        changes["current_value"] = float(current_value)
        changes["value_date"] = (parse_date(value_date) or date_cls.today()).isoformat()
    if not changes:
        return _err("no changes provided")
    preview = {
        "kind": "update_asset",
        "target": {"id": str(asset.id), "name": asset.name, "type": asset.type},
        "changes": changes,
        "apply_endpoint": f"PATCH /api/assets/{asset.id}",
    }
    if _can_apply(ctx, apply):
        updated = asset
        if update_data:
            updated = await asset_service.update_asset(
                session, asset.id, ws_id, ctx.user_id, AssetUpdate(**update_data)
            )
            if updated is None:
                return {**preview, "error": "asset not found"}
        if current_value is not None:
            await asset_service.add_asset_value(
                session,
                asset.id,
                ws_id,
                AssetValueCreate(
                    amount=Decimal(str(current_value)),
                    date=parse_date(value_date) or date_cls.today(),
                ),
            )
        return {**preview, "applied": True, "id": str(updated.id if updated else asset.id)}
    return preview


@tool(
    name="propose_delete_asset",
    description=_PROPOSAL_PREFACE + "Preview deleting a holding. Prefer archive via propose_update_asset unless the user wants it gone.",
    parameters={
        "type": "object",
        "properties": {
            "asset_id": {"type": "string", "format": "uuid"},
            "apply": _APPLY_FIELD,
        },
        "required": ["asset_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "assets"],
)
async def propose_delete_asset(
    *,
    session: AsyncSession,
    ctx: CallContext,
    asset_id: str,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    asset = await asset_service.get_asset(session, parse_uuid(asset_id), ws_id)
    if asset is None:
        return _err("asset not found")
    preview = {
        "kind": "delete_asset",
        "target": {"id": str(asset.id), "name": asset.name},
        "apply_endpoint": f"DELETE /api/assets/{asset.id}",
    }
    if _can_apply(ctx, apply):
        ok = await asset_service.delete_asset(session, asset.id, ws_id)
        if not ok:
            return {**preview, "error": "asset not found"}
        return {**preview, "applied": True, "deleted": True}
    return preview


@tool(
    name="propose_asset_trade",
    description=_PROPOSAL_PREFACE
    + "Preview recording a buy or sell on an existing holding (quantity × price).",
    parameters={
        "type": "object",
        "properties": {
            "asset_id": {"type": "string", "format": "uuid"},
            "kind": {"type": "string", "enum": ["buy", "sell"]},
            "quantity": {"type": "number", "exclusiveMinimum": 0},
            "price": {"type": "number", "exclusiveMinimum": 0},
            "fee": {"type": "number", "minimum": 0},
            "date": {"type": "string", "format": "date"},
            "notes": {"type": "string"},
            "apply": _APPLY_FIELD,
        },
        "required": ["asset_id", "kind", "quantity", "price"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "assets"],
)
async def propose_asset_trade(
    *,
    session: AsyncSession,
    ctx: CallContext,
    asset_id: str,
    kind: str,
    quantity: float,
    price: float,
    fee: float | None = None,
    date: str | None = None,
    notes: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    asset = await asset_service.get_asset(session, parse_uuid(asset_id), ws_id)
    if asset is None:
        return _err("asset not found")
    trade_date = parse_date(date) or date_cls.today()
    proposed = {
        "asset_id": str(asset.id),
        "asset_name": asset.name,
        "kind": kind,
        "quantity": float(quantity),
        "price": float(price),
        "fee": float(fee or 0),
        "date": trade_date.isoformat(),
        "notes": notes,
    }
    preview = {
        "kind": "asset_trade",
        "proposed": proposed,
        "apply_endpoint": f"POST /api/assets/{asset.id}/transactions",
    }
    if _can_apply(ctx, apply):
        try:
            updated = await asset_transaction_service.add_transaction(
                session,
                asset.id,
                ws_id,
                AssetTransactionCreate(
                    kind=kind,
                    quantity=Decimal(str(quantity)),
                    price=Decimal(str(price)),
                    fee=Decimal(str(fee or 0)),
                    date=trade_date,
                    notes=notes,
                ),
            )
        except ValueError as exc:
            return {**preview, "error": str(exc)}
        if updated is None:
            return {**preview, "error": "asset not found"}
        return {**preview, "applied": True, "asset_id": str(updated.id)}
    return preview


# --- Groups / settlements --------------------------------------------------


@tool(
    name="propose_create_group",
    description=_PROPOSAL_PREFACE
    + "Preview creating an expense-sharing group (Splitwise-style).",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 100},
            "kind": {
                "type": "string",
                "enum": ["social", "cost_center", "project", "client", "other"],
                "default": "social",
            },
            "currency": {"type": "string"},
            "apply": _APPLY_FIELD,
        },
        "required": ["name"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "groups"],
)
async def propose_create_group(
    *,
    session: AsyncSession,
    ctx: CallContext,
    name: str,
    kind: str = "social",
    currency: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    resolved = (currency or await _default_currency(session, ws_id)).upper()
    proposed = {"name": name.strip(), "kind": kind, "default_currency": resolved}
    preview = {"kind": "create_group", "proposed": proposed, "apply_endpoint": "POST /api/groups"}
    if _can_apply(ctx, apply):
        try:
            created = await group_service.create_group(
                session,
                ws_id,
                ctx.user_id,
                GroupCreate(name=proposed["name"], kind=kind, default_currency=resolved),
            )
        except ValueError as exc:
            return {**preview, "error": str(exc)}
        return {**preview, "applied": True, "id": str(created.id)}
    return preview


@tool(
    name="propose_add_group_member",
    description=_PROPOSAL_PREFACE
    + "Preview adding a person to an expense group. is_self marks the user.",
    parameters={
        "type": "object",
        "properties": {
            "group_id": {"type": "string", "format": "uuid"},
            "name": {"type": "string", "minLength": 1, "maxLength": 100},
            "is_self": {"type": "boolean", "default": False},
            "apply": _APPLY_FIELD,
        },
        "required": ["group_id", "name"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "groups"],
)
async def propose_add_group_member(
    *,
    session: AsyncSession,
    ctx: CallContext,
    group_id: str,
    name: str,
    is_self: bool = False,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    group = await group_service.get_group(session, parse_uuid(group_id), ws_id)
    if group is None:
        return _err("group not found")
    proposed = {"group_id": str(group.id), "group_name": group.name, "name": name.strip(), "is_self": bool(is_self)}
    preview = {
        "kind": "add_group_member",
        "proposed": proposed,
        "apply_endpoint": f"POST /api/groups/{group.id}/members",
    }
    if _can_apply(ctx, apply):
        try:
            created = await group_service.create_member(
                session,
                group.id,
                ws_id,
                GroupMemberCreate(name=proposed["name"], is_self=bool(is_self)),
            )
        except ValueError as exc:
            return {**preview, "error": str(exc)}
        if created is None:
            return {**preview, "error": "group not found"}
        return {**preview, "applied": True, "id": str(created.id)}
    return preview


@tool(
    name="propose_create_settlement",
    description=_PROPOSAL_PREFACE
    + (
        "Preview recording that one group member paid another (settle up). "
        "Pass member ids from list_groups. Optional account_id books a "
        "matching payment transaction for the payer."
    ),
    parameters={
        "type": "object",
        "properties": {
            "group_id": {"type": "string", "format": "uuid"},
            "from_member_id": {"type": "string", "format": "uuid"},
            "to_member_id": {"type": "string", "format": "uuid"},
            "amount": {"type": "number", "exclusiveMinimum": 0},
            "currency": {"type": "string"},
            "date": {"type": "string", "format": "date"},
            "account_id": {"type": "string", "format": "uuid"},
            "notes": {"type": "string"},
            "apply": _APPLY_FIELD,
        },
        "required": ["group_id", "from_member_id", "to_member_id", "amount"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "groups"],
)
async def propose_create_settlement(
    *,
    session: AsyncSession,
    ctx: CallContext,
    group_id: str,
    from_member_id: str,
    to_member_id: str,
    amount: float,
    currency: str | None = None,
    date: str | None = None,
    account_id: str | None = None,
    notes: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    group = await group_service.get_group(session, parse_uuid(group_id), ws_id)
    if group is None:
        return _err("group not found")
    when = parse_date(date) or date_cls.today()
    resolved = (currency or group.default_currency or await _default_currency(session, ws_id)).upper()
    proposed = {
        "group_id": str(group.id),
        "group_name": group.name,
        "from_member_id": from_member_id,
        "to_member_id": to_member_id,
        "amount": float(amount),
        "currency": resolved,
        "date": when.isoformat(),
        "account_id": account_id,
        "notes": notes,
    }
    preview = {
        "kind": "create_settlement",
        "proposed": proposed,
        "apply_endpoint": f"POST /api/groups/{group.id}/settlements",
    }
    if _can_apply(ctx, apply):
        try:
            created = await settlement_service.create_settlement(
                session,
                group.id,
                ws_id,
                ctx.user_id,
                GroupSettlementCreate(
                    from_member_id=parse_uuid(from_member_id),
                    to_member_id=parse_uuid(to_member_id),
                    amount=Decimal(str(amount)),
                    currency=resolved,
                    date=when,
                    account_id=parse_uuid(account_id) if account_id else None,
                    notes=notes,
                ),
            )
        except (ValueError, PermissionError) as exc:
            return {**preview, "error": str(exc)}
        if created is None:
            return {**preview, "error": "group not found"}
        return {**preview, "applied": True, "id": str(created.id)}
    return preview
