"""Propose-mutations.

In Securo's own runtime these tools NEVER write to the DB. They return a
structured proposal that the agent surfaces to the user. The user confirms
in the UI, which calls the existing Securo write endpoint to do the real
change. Keeps MCP safe and gives the user a chance to review.

When called via an *external* token (Claude Desktop, n8n, custom clients
— `ctx.external` is true), there is no Apply button to render. In that
case the tools accept an extra `apply: true` flag: first call returns
the preview as usual; a follow-up call with `apply=true` performs the
write directly. Internal callers never set `apply`, so behavior is
unchanged for Securo's own UI.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.category import Category
from app.models.group import Group, GroupMember
from app.models.payee import Payee
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.schemas.budget import BudgetCreate
from app.schemas.category import CategoryCreate
from app.schemas.goal import GoalCreate
from app.schemas.recurring_transaction import (
    RecurringTransactionCreate,
    RecurringTransactionUpdate,
    WeekendAdjustment,
)
from app.schemas.rule import RuleAction, RuleCondition, RuleCreate
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.schemas.transaction_split import TransactionSplitInput, TransactionSplitsInput
from app.services import (
    budget_service,
    category_service,
    goal_service,
    recurring_transaction_service,
    rule_service,
    transaction_service,
)
from mcp_server.auth import CallContext
from mcp_server.registry import tool
from mcp_server.tools._helpers import (
    num,
    parse_date,
    parse_uuid,
    parse_uuid_list,
    resolve_workspace_id,
)


# Repeated in EVERY propose_* tool description. The LLM reads these when
# deciding when to use a tool AND when describing the result to the user.
# The strong "REQUIRES USER CONFIRMATION" framing prevents the model from
# saying "Pronto! Criei…" / "Done! I added…" — the action is NOT executed
# by the tool call; it only takes effect when the user clicks Apply (or
# the caller re-invokes with apply=true on the external transport).
_PROPOSAL_PREFACE = (
    "[PROPOSAL — PREVIEW ONLY, NOT EXECUTED. The user MUST confirm before "
    "the change happens. In Securo's UI an Apply button + diff card render "
    "automatically — do not duplicate the details in your reply. When you "
    "are running through an external MCP client (no Apply button in chat), "
    "pass apply=true on a follow-up call AFTER the user explicitly "
    "confirms in the conversation. Never set apply=true on the first call. "
    "Describe results as 'I prepared a proposal…' / 'Here's a preview…' — "
    "NEVER as 'I created' / 'Done' / 'Ready' unless the response includes "
    "applied=true.] "
)

# Apply flag, attached to every propose_* tool's parameters. Default false.
_APPLY_FIELD = {
    "type": "boolean",
    "default": False,
    "description": (
        "External clients only. When true (and the call is authenticated "
        "with an external MCP token), executes the change instead of "
        "returning a preview. Ignored by Securo's internal runtime."
    ),
}


def _can_apply(ctx: CallContext, apply: bool) -> bool:
    """Gate: writes only happen when the caller is external AND set apply."""
    return bool(apply) and ctx.external


# DB columns: description String(500), notes String(1000). Agents often
# summarize the user message into `description` and drop free-form detail.
# These helpers keep every user-provided detail by parking overflow in notes
# and clamping to column limits without inventing content.
_DESC_MAX = 500
_NOTES_MAX = 1000


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _join_notes(*parts: str | None) -> str | None:
    chunks = [p.strip() for p in parts if p and p.strip()]
    if not chunks:
        return None
    # Prefer unique order-preserving chunks so we do not duplicate when the
    # model already put the same sentence in both fields.
    seen: set[str] = set()
    unique: list[str] = []
    for c in chunks:
        key = c.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    joined = "\n".join(unique)
    if len(joined) <= _NOTES_MAX:
        return joined
    return joined[: _NOTES_MAX - 1].rstrip() + "…"


def _normalize_description_and_notes(
    description: str,
    notes: str | None,
) -> tuple[str, str | None]:
    """Keep a short title in description; never lose user detail.

    If description exceeds 500 chars, the overflow moves into notes.
    Notes are clamped to 1000 chars. Content is never invented — only
    relocated / truncated with an ellipsis when the DB limit forces it.
    """
    desc = (description or "").strip()
    note = _clean_optional_text(notes)
    overflow: str | None = None
    if len(desc) > _DESC_MAX:
        # Keep a clean cut near a space when possible.
        cut = desc.rfind(" ", 0, _DESC_MAX - 1)
        if cut < int(_DESC_MAX * 0.6):
            cut = _DESC_MAX - 1
        overflow = desc[cut:].strip()
        desc = desc[:cut].rstrip(" -–,;:") or desc[:_DESC_MAX]
    note = _join_notes(note, overflow)
    return desc, note



def _tx_snapshot(
    tx: Transaction,
    *,
    account_name: str | None = None,
    category_name: str | None = None,
    payee_name: str | None = None,
) -> dict[str, Any]:
    return {
        "id": str(tx.id),
        "description": tx.description,
        "amount": num(tx.amount),
        "currency": tx.currency,
        "type": tx.type,
        "date": tx.date.isoformat() if tx.date else None,
        "account_id": str(tx.account_id) if tx.account_id else None,
        "account_name": account_name,
        "category_id": str(tx.category_id) if tx.category_id else None,
        "category_name": category_name,
        "payee_id": str(tx.payee_id) if tx.payee_id else None,
        "payee_name": payee_name,
        "notes": tx.notes,
        "status": tx.status,
        "is_ignored": bool(getattr(tx, "is_ignored", False)),
    }


async def _workspace_account(
    session: AsyncSession, ws_id, account_id
) -> Account | None:
    if account_id is None:
        return None
    return (
        await session.execute(
            select(Account).where(Account.id == account_id, Account.workspace_id == ws_id)
        )
    ).scalar_one_or_none()


@tool(
    name="propose_categorize",
    description=_PROPOSAL_PREFACE
    + (
        "Build a preview for re-categorizing one or more transactions. "
        "Returns a summary of what would change and the resolved category."
    ),
    parameters={
        "type": "object",
        "properties": {
            "transaction_ids": {
                "type": "array",
                "items": {"type": "string", "format": "uuid"},
                "minItems": 1,
            },
            "category_id": {"type": "string", "format": "uuid"},
            "apply": _APPLY_FIELD,
        },
        "required": ["transaction_ids", "category_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "transactions"],
)
async def propose_categorize(
    *,
    session: AsyncSession,
    ctx: CallContext,
    transaction_ids: list[str],
    category_id: str,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    cat_id = parse_uuid(category_id)
    cat = (
        await session.execute(
            select(Category).where(Category.id == cat_id, Category.workspace_id == ws_id)
        )
    ).scalar_one_or_none()
    if cat is None:
        return {"error": "category not found"}

    tx_ids = parse_uuid_list(transaction_ids) or []
    txs = (
        (
            await session.execute(
                select(Transaction).where(
                    Transaction.id.in_(tx_ids), Transaction.workspace_id == ws_id
                )
            )
        )
        .scalars()
        .all()
    )

    affected = [
        {
            "id": str(t.id),
            "description": t.description,
            "amount": num(t.amount),
            "currency": t.currency,
            "current_category_id": str(t.category_id) if t.category_id else None,
        }
        for t in txs
    ]
    preview = {
        "kind": "categorize",
        "target_category": {"id": str(cat.id), "name": cat.name},
        "affected_count": len(affected),
        "affected": affected,
        "missing_ids": [str(t) for t in tx_ids if str(t) not in {a["id"] for a in affected}],
        "apply_endpoint": "POST /api/transactions/categorize",
    }

    if _can_apply(ctx, apply):
        if not affected:
            return {**preview, "error": "no matching transactions to update"}
        tx_uuids = [u for a in affected if (u := parse_uuid(a["id"])) is not None]
        updated = await transaction_service.bulk_update_category(
            session, ws_id, tx_uuids, cat.id
        )
        return {**preview, "applied": True, "updated_count": updated}

    return preview


@tool(
    name="propose_create_category",
    description=_PROPOSAL_PREFACE
    + (
        "Preview the creation of a new category. Returns the proposed shape "
        "and any name collision detected."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 100},
            "group_id": {"type": "string", "format": "uuid"},
            "icon": {"type": "string"},
            "color": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
            "apply": _APPLY_FIELD,
        },
        "required": ["name"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "categories"],
)
async def propose_create_category(
    *,
    session: AsyncSession,
    ctx: CallContext,
    name: str,
    group_id: str | None = None,
    icon: str | None = None,
    color: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    existing = (
        await session.execute(
            select(Category.id, Category.name).where(
                Category.workspace_id == ws_id,
                Category.name.ilike(name.strip()),
            )
        )
    ).first()
    preview = {
        "kind": "create_category",
        "proposed": {
            "name": name.strip(),
            "group_id": str(parse_uuid(group_id)) if group_id else None,
            "icon": icon or "circle-help",
            "color": color or "#6B7280",
        },
        "name_collision": {"id": str(existing.id), "name": existing.name} if existing else None,
        "apply_endpoint": "POST /api/categories",
    }

    if _can_apply(ctx, apply):
        if existing:
            return {**preview, "error": f"category named {existing.name!r} already exists"}
        created = await category_service.create_category(
            session,
            ws_id,
            ctx.user_id,
            CategoryCreate(
                name=preview["proposed"]["name"],
                group_id=parse_uuid(group_id) if group_id else None,
                icon=preview["proposed"]["icon"],
                color=preview["proposed"]["color"],
            ),
        )
        return {**preview, "applied": True, "id": str(created.id)}

    return preview


@tool(
    name="propose_create_budget",
    description=_PROPOSAL_PREFACE
    + (
        "Preview a budget creation for a category and month. If that "
        "category already has a budget, this tool does NOT create a "
        "second row — it returns existing_budget_id and tells you to "
        "call propose_update_budget. STRICT: if the user mentions a "
        "category that does NOT match an existing one (call list_categories "
        "first to verify), do not silently substitute a different category "
        "— instead, ask the user to confirm an alternative or call "
        "propose_create_category first to add the missing one."
    ),
    parameters={
        "type": "object",
        "properties": {
            "category_id": {"type": "string", "format": "uuid"},
            "month": {"type": "string", "format": "date"},
            "amount": {"type": "number", "exclusiveMinimum": 0},
            "currency": {"type": "string"},
            "is_recurring": {"type": "boolean", "default": False},
            "apply": _APPLY_FIELD,
        },
        "required": ["category_id", "month", "amount"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "budgets"],
)
async def propose_create_budget(
    *,
    session: AsyncSession,
    ctx: CallContext,
    category_id: str,
    month: str,
    amount: float,
    currency: str | None = None,
    is_recurring: bool = False,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    cat_id = parse_uuid(category_id)
    target_month = (parse_date(month) or date.today()).replace(day=1)

    cat = (
        await session.execute(
            select(Category).where(Category.id == cat_id, Category.workspace_id == ws_id)
        )
    ).scalar_one_or_none()
    if cat is None:
        return {"error": "category not found"}

    existing_rows = await budget_service.get_budgets(session, ws_id, month=target_month)
    existing = next((b for b in existing_rows if b.category_id == cat.id), None)
    if existing is not None:
        return {
            "error": "budget already exists — call propose_update_budget with this existing_budget_id; do not create a second row",
            "existing_budget_id": str(existing.id),
            "existing_amount": num(existing.amount),
            "is_recurring": bool(existing.is_recurring),
            "category_id": str(cat.id),
            "category_name": cat.name,
            "next_tool": "propose_update_budget",
            "next_args": {"budget_id": str(existing.id), "amount": float(amount)},
        }

    preview = {
        "kind": "create_budget",
        "proposed": {
            "category_id": str(cat.id),
            "category_name": cat.name,
            "month": target_month.isoformat(),
            "amount": float(amount),
            "currency": currency,
            "is_recurring": is_recurring,
        },
        "apply_endpoint": "POST /api/budgets",
    }

    if _can_apply(ctx, apply):
        try:
            created = await budget_service.create_budget(
                session,
                ws_id,
                ctx.user_id,
                BudgetCreate(
                    category_id=cat.id,
                    amount=Decimal(str(amount)),
                    month=target_month,
                    is_recurring=is_recurring,
                ),
            )
        except IntegrityError:
            await session.rollback()
            return {
                "error": "budget already exists — call propose_update_budget; do not create a second row",
                "category_id": str(cat.id),
                "category_name": cat.name,
                "next_tool": "propose_update_budget",
            }
        return {**preview, "applied": True, "id": str(created.id)}

    return preview


@tool(
    name="propose_create_transaction",
    description=_PROPOSAL_PREFACE
    + (
        "Build a preview for adding a one-off transaction (e.g. 'add a "
        "R$50 lunch today'). Validates the account/category/payee exist; "
        "leaves currency to the account's default when not provided.\n\n"
        "Field split (critical — do not drop user detail):\n"
        "- `description`: short payee/merchant title only (≤500).\n"
        "- `notes`: ALL free-form user detail — receipt lines, purpose, "
        "location, card/SMS text, trip ids, 'keep note: …', weekly stock, "
        "etc. Pass the user's words; do not summarize them away. If the "
        "only text field you have is long, put the overflow in `notes`.\n"
        "- `payee_id`: optional id from `list_payees` when there is an "
        "exact/known match. Never invent a payee name or id.\n"
        "- `category_id`: optional id from `list_categories` (or a prior "
        "similar txn). Leave unset rather than guessing a fake category.\n\n"
        "Group splits: pass `group_id` + `splits` to attach a Splitwise-"
        "style breakdown. `splits.share_type='equal'` divides the amount "
        "evenly across the listed `member_ids` — perfect for 'crie no "
        "grupo dos Amigos e divida igualmente'. Use `'exact'` with a "
        "`share_amount` per member, or `'percent'` with `share_pct` per "
        "member, for custom shares. All members must belong to the same "
        "group as `group_id`. Call `list_groups` first to fetch IDs."
    ),
    parameters={
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500,
                "description": (
                    "Short payee/merchant title for the row (e.g. 'Big Bazaar'). "
                    "Do NOT stuff receipt notes here — put those in `notes`. "
                    "If this exceeds 500 chars the server moves the overflow into notes."
                ),
            },
            "amount": {
                "type": "number",
                "exclusiveMinimum": 0,
                "description": "Absolute value, always positive — direction comes from `type`",
            },
            "type": {
                "type": "string",
                "enum": ["debit", "credit"],
                "description": "debit = expense, credit = income",
            },
            "account_id": {"type": "string", "format": "uuid"},
            "category_id": {
                "type": "string",
                "format": "uuid",
                "description": "Optional category id from list_categories. Omit if unknown — do not invent.",
            },
            "payee_id": {
                "type": "string",
                "format": "uuid",
                "description": "Optional payee id from list_payees when there is a factual match. Omit if unknown — do not invent a merchant.",
            },
            "date": {"type": "string", "format": "date", "description": "Defaults to today"},
            "currency": {"type": "string", "description": "Defaults to the account's currency"},
            "notes": {
                "type": "string",
                "maxLength": 1000,
                "description": (
                    "REQUIRED whenever the user gave any free-form detail beyond "
                    "amount/payee/date. Persist their words: purpose ('for groceries "
                    "weekly stock'), receipt notes ('bought milk+eggs'), location, "
                    "card/SMS text, trip/voucher ids, etc. Never drop or heavily "
                    "summarize. Leave unset only when there truly is no extra detail."
                ),
            },
            "group_id": {
                "type": "string",
                "format": "uuid",
                "description": "Optional: attach to an expense-sharing group",
            },
            "splits": {
                "type": "object",
                "description": "Required when `group_id` is set. Defines how the amount is split among group members.",
                "properties": {
                    "share_type": {"type": "string", "enum": ["equal", "exact", "percent"]},
                    "members": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "member_id": {"type": "string", "format": "uuid"},
                                "share_amount": {
                                    "type": "number",
                                    "description": "Required for share_type='exact' (sum must equal `amount`)",
                                },
                                "share_pct": {
                                    "type": "number",
                                    "description": "Required for share_type='percent' (must sum to 100)",
                                },
                            },
                            "required": ["member_id"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["share_type", "members"],
                "additionalProperties": False,
            },
            "apply": _APPLY_FIELD,
        },
        "required": ["description", "amount", "type", "account_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "transactions"],
)
async def propose_create_transaction(
    *,
    session: AsyncSession,
    ctx: CallContext,
    description: str,
    amount: float,
    type: str,
    account_id: str,
    category_id: str | None = None,
    payee_id: str | None = None,
    date: str | None = None,
    currency: str | None = None,
    notes: str | None = None,
    group_id: str | None = None,
    splits: dict[str, Any] | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    description, notes = _normalize_description_and_notes(description, notes)
    ws_id = await resolve_workspace_id(session, ctx)
    acc_id = parse_uuid(account_id)
    acc = (
        await session.execute(
            select(Account).where(Account.id == acc_id, Account.workspace_id == ws_id)
        )
    ).scalar_one_or_none()
    if acc is None:
        return {"error": "account not found"}

    cat = None
    if category_id:
        cat = (
            await session.execute(
                select(Category).where(
                    Category.id == parse_uuid(category_id), Category.workspace_id == ws_id
                )
            )
        ).scalar_one_or_none()
        if cat is None:
            return {"error": "category not found"}

    payee = None
    if payee_id:
        payee = (
            await session.execute(
                select(Payee).where(
                    Payee.id == parse_uuid(payee_id), Payee.workspace_id == ws_id
                )
            )
        ).scalar_one_or_none()
        if payee is None:
            return {"error": "payee not found"}

    # Validate group + splits (if any) so the preview is honest.
    splits_preview: list[dict[str, Any]] | None = None
    group_name: str | None = None
    if group_id or splits:
        if not (group_id and splits):
            return {"error": "group_id and splits must be provided together"}
        gid = parse_uuid(group_id)
        # Group ownership stays user-scoped (Splitwise authorship check) —
        # the user_id column on `groups` represents the owner, not a
        # tenant filter.
        group = (
            await session.execute(
                select(Group).where(Group.id == gid, Group.user_id == ctx.user_id)
            )
        ).scalar_one_or_none()
        if group is None:
            return {"error": "group not found"}
        group_name = group.name

        share_type = splits.get("share_type")
        if share_type not in ("equal", "exact", "percent"):
            return {"error": f"invalid share_type: {share_type!r}"}
        members_in = splits.get("members") or []
        if not members_in:
            return {"error": "splits.members must not be empty"}
        member_ids = [parse_uuid(m["member_id"]) for m in members_in]
        rows = (
            (
                await session.execute(
                    select(GroupMember).where(
                        GroupMember.id.in_(member_ids), GroupMember.group_id == gid
                    )
                )
            )
            .scalars()
            .all()
        )
        if len(rows) != len(set(member_ids)):
            return {"error": "one or more members do not belong to the given group"}
        name_by_id = {m.id: m.name for m in rows}

        # Materialize a preview for the UI/LLM. The actual write happens
        # via POST /api/transactions which re-runs the same math.
        n = len(members_in)
        amt = float(amount)
        if share_type == "equal":
            per = round(amt / n, 2)
            residual = round(amt - per * (n - 1), 2)
            splits_preview = [
                {
                    "member_id": str(m["member_id"]),
                    "member_name": name_by_id.get(parse_uuid(m["member_id"]), "?"),
                    "share_amount": (residual if i == n - 1 else per),
                }
                for i, m in enumerate(members_in)
            ]
        elif share_type == "exact":
            total = round(sum((float(m.get("share_amount") or 0) for m in members_in), 0.0), 2)
            if abs(total - amt) > 0.01:
                return {"error": f"exact share amounts sum to {total}, expected {amt}"}
            splits_preview = [
                {
                    "member_id": str(m["member_id"]),
                    "member_name": name_by_id.get(parse_uuid(m["member_id"]), "?"),
                    "share_amount": float(m.get("share_amount") or 0),
                }
                for m in members_in
            ]
        else:  # percent
            pct_sum = round(sum((float(m.get("share_pct") or 0) for m in members_in), 0.0), 2)
            if abs(pct_sum - 100.0) > 0.01:
                return {"error": f"percent shares sum to {pct_sum}, expected 100"}
            running = 0.0
            splits_preview = []
            for i, m in enumerate(members_in):
                if i == n - 1:
                    share = round(amt - running, 2)
                else:
                    share = round(amt * float(m.get("share_pct") or 0) / 100.0, 2)
                    running += share
                splits_preview.append(
                    {
                        "member_id": str(m["member_id"]),
                        "member_name": name_by_id.get(parse_uuid(m["member_id"]), "?"),
                        "share_amount": share,
                        "share_pct": float(m.get("share_pct") or 0),
                    }
                )

    target_date = parse_date(date) or _today()
    proposed: dict[str, Any] = {
        "description": description,
        "amount": float(amount),
        "currency": (currency or acc.currency or "USD").upper(),
        "type": type,
        "date": target_date.isoformat(),
        "account_id": str(acc.id),
        "account_name": acc.name,
        "category_id": str(cat.id) if cat else None,
        "category_name": cat.name if cat else None,
        "payee_id": str(payee.id) if payee else None,
        "payee_name": payee.name if payee else None,
        "notes": notes,
    }
    if splits_preview is not None:
        assert splits is not None
        proposed["group_id"] = group_id
        proposed["group_name"] = group_name
        proposed["splits"] = {
            "share_type": splits["share_type"],
            "items": splits_preview,
        }
    preview = {
        "kind": "create_transaction",
        "proposed": proposed,
        "apply_endpoint": "POST /api/transactions",
    }

    if _can_apply(ctx, apply):
        # Re-shape splits for the service. The propose tool used `member_id`
        # but TransactionSplitInput uses `group_member_id`.
        splits_payload: TransactionSplitsInput | None = None
        if splits is not None:
            splits_payload = TransactionSplitsInput(
                share_type=splits["share_type"],
                splits=[
                    TransactionSplitInput(
                        group_member_id=mid,
                        share_amount=Decimal(str(m["share_amount"]))
                        if m.get("share_amount") is not None
                        else None,
                        share_pct=Decimal(str(m["share_pct"]))
                        if m.get("share_pct") is not None
                        else None,
                    )
                    for m in splits["members"]
                    if (mid := parse_uuid(m["member_id"])) is not None
                ],
            )
        try:
            created = await transaction_service.create_transaction(
                session,
                ws_id,
                ctx.user_id,
                TransactionCreate(
                    description=proposed["description"],
                    amount=Decimal(str(amount)),
                    date=target_date,
                    type=type,
                    account_id=acc.id,
                    category_id=cat.id if cat else None,
                    payee_id=payee.id if payee else None,
                    currency=proposed["currency"],
                    notes=notes,
                    splits=splits_payload,
                ),
            )
        except ValueError as exc:
            return {**preview, "error": str(exc)}
        return {**preview, "applied": True, "id": str(created.id)}

    return preview


@tool(
    name="propose_update_transaction",
    description=_PROPOSAL_PREFACE
    + (
        "Build a preview for editing an already-booked transaction "
        "(e.g. 'move those two entries to ICICI Bank', 'change the amount "
        "to ₹450', 'fix the date'). Pass the transaction_id from "
        "list_transactions and only the fields you want to change. "
        "Use this for booked rows — not propose_create_transaction, and "
        "not the web app. For a recurring template use "
        "propose_update_recurring_transaction instead."
    ),
    parameters={
        "type": "object",
        "properties": {
            "transaction_id": {"type": "string", "format": "uuid"},
            "description": {"type": "string", "minLength": 1, "maxLength": 500},
            "amount": {
                "type": "number",
                "exclusiveMinimum": 0,
                "description": "Absolute value, always positive — direction comes from `type`",
            },
            "date": {"type": "string", "format": "date"},
            "type": {
                "type": "string",
                "enum": ["debit", "credit"],
                "description": "debit = expense, credit = income",
            },
            "currency": {"type": "string"},
            "account_id": {
                "type": "string",
                "format": "uuid",
                "description": "Move the booking to another account (from list_accounts)",
            },
            "category_id": {"type": "string", "format": "uuid"},
            "payee_id": {
                "type": "string",
                "format": "uuid",
                "description": "Payee id from list_payees. Omit rather than inventing.",
            },
            "notes": {
                "type": "string",
                "maxLength": 1000,
                "description": (
                    "Replace notes with the full user-provided detail. Do not "
                    "strip receipt / purpose text when editing other fields — "
                    "re-pass existing notes if they must stay."
                ),
            },
            "is_ignored": {"type": "boolean"},
            "status": {"type": "string", "enum": ["posted", "pending"]},
            "apply_to": {
                "type": "string",
                "enum": ["this", "future", "all"],
                "default": "this",
                "description": (
                    "Installment series only. 'this' edits one row; "
                    "'future' this and later parcels; 'all' the whole series."
                ),
            },
            "apply_to_transfer_pair": {
                "type": "boolean",
                "default": False,
                "description": "When true, also apply matching fields to the other transfer leg.",
            },
            "apply": _APPLY_FIELD,
        },
        "required": ["transaction_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "transactions"],
)
async def propose_update_transaction(
    *,
    session: AsyncSession,
    ctx: CallContext,
    transaction_id: str,
    description: str | None = None,
    amount: float | None = None,
    date: str | None = None,
    type: str | None = None,
    currency: str | None = None,
    account_id: str | None = None,
    category_id: str | None = None,
    payee_id: str | None = None,
    notes: str | None = None,
    is_ignored: bool | None = None,
    status: str | None = None,
    apply_to: str = "this",
    apply_to_transfer_pair: bool = False,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    tid = parse_uuid(transaction_id)
    tx = (
        await session.execute(
            select(Transaction).where(
                Transaction.id == tid, Transaction.workspace_id == ws_id
            )
        )
    ).scalar_one_or_none()
    if tx is None:
        return {"error": "transaction not found"}

    new_acc = None
    if account_id is not None:
        new_acc = await _workspace_account(session, ws_id, parse_uuid(account_id))
        if new_acc is None:
            return {"error": "account not found"}

    cat = None
    if category_id is not None:
        cat = (
            await session.execute(
                select(Category).where(
                    Category.id == parse_uuid(category_id), Category.workspace_id == ws_id
                )
            )
        ).scalar_one_or_none()
        if cat is None:
            return {"error": "category not found"}

    payee = None
    if payee_id is not None:
        payee = (
            await session.execute(
                select(Payee).where(
                    Payee.id == parse_uuid(payee_id), Payee.workspace_id == ws_id
                )
            )
        ).scalar_one_or_none()
        if payee is None:
            return {"error": "payee not found"}

    parsed_date = parse_date(date) if date is not None else None
    if date is not None and parsed_date is None:
        return {"error": "invalid date"}

    update_data: dict[str, Any] = {}
    changes: dict[str, Any] = {}
    # Normalize description/notes together when either is touched so a long
    # description still parks overflow in notes instead of failing the DB.
    if description is not None or notes is not None:
        # When only notes changes, keep the existing description as the base
        # title; when only description changes, keep existing notes.
        base_desc = description if description is not None else (tx.description or "")
        base_notes = notes if notes is not None else tx.notes
        norm_desc, norm_notes = _normalize_description_and_notes(base_desc, base_notes)
        if description is not None or norm_desc != (tx.description or ""):
            update_data["description"] = norm_desc
            changes["description"] = norm_desc
        if notes is not None or norm_notes != tx.notes:
            update_data["notes"] = norm_notes
            changes["notes"] = norm_notes
    if amount is not None:
        update_data["amount"] = Decimal(str(amount))
        changes["amount"] = float(amount)
    if parsed_date is not None:
        update_data["date"] = parsed_date
        changes["date"] = parsed_date.isoformat()
    if type is not None:
        update_data["type"] = type
        changes["type"] = type
    if currency is not None:
        update_data["currency"] = currency.upper()
        changes["currency"] = currency.upper()
    if new_acc is not None:
        update_data["account_id"] = new_acc.id
        changes["account_id"] = str(new_acc.id)
        changes["account_name"] = new_acc.name
    if cat is not None:
        update_data["category_id"] = cat.id
        changes["category_id"] = str(cat.id)
        changes["category_name"] = cat.name
    if payee is not None:
        update_data["payee_id"] = payee.id
        changes["payee_id"] = str(payee.id)
        changes["payee_name"] = payee.name
    if is_ignored is not None:
        update_data["is_ignored"] = bool(is_ignored)
        changes["is_ignored"] = bool(is_ignored)
    if status is not None:
        update_data["status"] = status
        changes["status"] = status
    if apply_to != "this":
        update_data["apply_to"] = apply_to
        changes["apply_to"] = apply_to
    if apply_to_transfer_pair:
        update_data["apply_to_transfer_pair"] = True
        changes["apply_to_transfer_pair"] = True

    if not changes:
        return {"error": "no changes provided"}

    current_acc = await _workspace_account(session, ws_id, tx.account_id)
    current_cat = None
    if tx.category_id:
        current_cat = (
            await session.execute(
                select(Category).where(
                    Category.id == tx.category_id, Category.workspace_id == ws_id
                )
            )
        ).scalar_one_or_none()
    current_payee = None
    if tx.payee_id:
        current_payee = (
            await session.execute(
                select(Payee).where(
                    Payee.id == tx.payee_id, Payee.workspace_id == ws_id
                )
            )
        ).scalar_one_or_none()

    preview = {
        "kind": "update_transaction",
        "target": _tx_snapshot(
            tx,
            account_name=current_acc.name if current_acc else None,
            category_name=current_cat.name if current_cat else None,
            payee_name=current_payee.name if current_payee else None,
        ),
        "changes": changes,
        "apply_endpoint": f"PATCH /api/transactions/{tx.id}",
    }

    if _can_apply(ctx, apply):
        try:
            updated = await transaction_service.update_transaction(
                session, tx.id, ws_id, ctx.user_id, TransactionUpdate(**update_data)
            )
        except ValueError as exc:
            return {**preview, "error": str(exc)}
        if updated is None:
            return {**preview, "error": "transaction not found"}
        return {**preview, "applied": True, "id": str(updated.id)}

    return preview


@tool(
    name="propose_delete_transaction",
    description=_PROPOSAL_PREFACE
    + (
        "Build a preview for deleting one or more already-booked "
        "transactions (e.g. 'delete those two wrong entries'). Pass ids "
        "from list_transactions. Use this instead of sending the user to "
        "the web app. For a recurring template use "
        "propose_cancel_recurring_transaction. apply_to is for installment "
        "series only (this/future/all)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "transaction_ids": {
                "type": "array",
                "items": {"type": "string", "format": "uuid"},
                "minItems": 1,
            },
            "apply_to": {
                "type": "string",
                "enum": ["this", "future", "all"],
                "default": "this",
                "description": (
                    "Installment series only. 'this' deletes the listed rows; "
                    "'future' also later parcels of each series; 'all' every "
                    "row in those series."
                ),
            },
            "apply": _APPLY_FIELD,
        },
        "required": ["transaction_ids"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "transactions"],
)
async def propose_delete_transaction(
    *,
    session: AsyncSession,
    ctx: CallContext,
    transaction_ids: list[str],
    apply_to: str = "this",
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    tx_ids = parse_uuid_list(transaction_ids) or []
    if not tx_ids:
        return {"error": "no valid transaction ids"}

    txs = (
        (
            await session.execute(
                select(Transaction).where(
                    Transaction.id.in_(tx_ids), Transaction.workspace_id == ws_id
                )
            )
        )
        .scalars()
        .all()
    )
    found_ids = {t.id for t in txs}
    acc_ids = {t.account_id for t in txs if t.account_id}
    accounts = (
        (
            await session.execute(
                select(Account).where(
                    Account.id.in_(acc_ids), Account.workspace_id == ws_id
                )
            )
        )
        .scalars()
        .all()
        if acc_ids
        else []
    )
    name_by_acc = {a.id: a.name for a in accounts}

    affected = [
        _tx_snapshot(t, account_name=name_by_acc.get(t.account_id)) for t in txs
    ]
    preview = {
        "kind": "delete_transaction",
        "apply_to": apply_to,
        "affected_count": len(affected),
        "affected": affected,
        "missing_ids": [str(t) for t in tx_ids if t not in found_ids],
        "apply_endpoint": (
            f"DELETE /api/transactions/{{id}}?apply_to={apply_to}"
            if len(tx_ids) == 1
            else "POST /api/transactions/bulk-delete"
        ),
    }

    if _can_apply(ctx, apply):
        if not txs:
            return {**preview, "error": "no matching transactions to delete"}
        deleted_ids: list[str] = []
        for tid in [t.id for t in txs]:
            ok = await transaction_service.delete_transaction(
                session, tid, ws_id, apply_to=apply_to
            )
            if ok:
                deleted_ids.append(str(tid))
        return {
            **preview,
            "applied": True,
            "deleted_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
        }

    return preview


@tool(
    name="propose_create_recurring_transaction",
    description=_PROPOSAL_PREFACE
    + (
        "Build a preview for adding a recurring transaction / subscription "
        "(e.g. 'Netflix R$55 every month on the 10th'). Frequency is one "
        "of weekly/monthly/quarterly/yearly. For monthly or quarterly use "
        "day_of_month (1-31). Default auto_generate=false (reminder-only; "
        "Securo will not auto-post). Set auto_generate=true only if the "
        "user explicitly wants the app to book the due date by itself."
    ),
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string", "minLength": 1, "maxLength": 500},
            "amount": {"type": "number", "exclusiveMinimum": 0},
            "type": {"type": "string", "enum": ["debit", "credit"]},
            "frequency": {"type": "string", "enum": ["weekly", "monthly", "quarterly", "yearly"]},
            "weekend_adjustment": {
                "type": "string",
                "enum": ["none", "previous_friday", "next_monday"],
                "default": "none",
            },
            "day_of_month": {"type": "integer", "minimum": 1, "maximum": 31, "description": "Required for monthly or quarterly"},
            "start_date": {"type": "string", "format": "date", "description": "Defaults to today"},
            "end_date": {"type": "string", "format": "date"},
            "account_id": {"type": "string", "format": "uuid"},
            "category_id": {"type": "string", "format": "uuid"},
            "currency": {"type": "string"},
            "auto_generate": {
                "type": "boolean",
                "default": False,
                "description": (
                    "When true, Securo's hourly job posts a real transaction "
                    "on the due date. Default false: reminder-only."
                ),
            },
            "apply": _APPLY_FIELD,
        },
        "required": ["description", "amount", "type", "frequency", "account_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "recurring"],
)
async def propose_create_recurring_transaction(
    *,
    session: AsyncSession,
    ctx: CallContext,
    description: str,
    amount: float,
    type: str,
    frequency: str,
    account_id: str,
    weekend_adjustment: WeekendAdjustment = "none",
    day_of_month: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    category_id: str | None = None,
    currency: str | None = None,
    auto_generate: bool = False,
    apply: bool = False,
) -> dict[str, Any]:
    if frequency in ("monthly", "quarterly") and not day_of_month:
        return {"error": "day_of_month is required for monthly or quarterly frequency"}
    ws_id = await resolve_workspace_id(session, ctx)
    acc = (
        await session.execute(
            select(Account).where(
                Account.id == parse_uuid(account_id), Account.workspace_id == ws_id
            )
        )
    ).scalar_one_or_none()
    if acc is None:
        return {"error": "account not found"}
    cat = None
    if category_id:
        cat = (
            await session.execute(
                select(Category).where(
                    Category.id == parse_uuid(category_id), Category.workspace_id == ws_id
                )
            )
        ).scalar_one_or_none()
        if cat is None:
            return {"error": "category not found"}

    target_start = parse_date(start_date) or _today()
    target_end = parse_date(end_date) if end_date else None
    resolved_currency = (currency or acc.currency or "USD").upper()
    preview = {
        "kind": "create_recurring_transaction",
        "proposed": {
            "description": description.strip(),
            "amount": float(amount),
            "currency": resolved_currency,
            "type": type,
            "frequency": frequency,
            "weekend_adjustment": weekend_adjustment,
            "day_of_month": int(day_of_month) if day_of_month else None,
            "start_date": target_start.isoformat(),
            "end_date": target_end.isoformat() if target_end else None,
            "account_id": str(acc.id),
            "account_name": acc.name,
            "category_id": str(cat.id) if cat else None,
            "category_name": cat.name if cat else None,
            "auto_generate": bool(auto_generate),
        },
        "apply_endpoint": "POST /api/recurring-transactions",
    }

    if _can_apply(ctx, apply):
        created = await recurring_transaction_service.create_recurring_transaction(
            session,
            ws_id,
            ctx.user_id,
            RecurringTransactionCreate(
                description=description.strip(),
                amount=Decimal(str(amount)),
                currency=resolved_currency,
                type=type,
                frequency=frequency,
                weekend_adjustment=weekend_adjustment,
                day_of_month=int(day_of_month) if day_of_month else None,
                start_date=target_start,
                end_date=target_end,
                account_id=acc.id,
                category_id=cat.id if cat else None,
                auto_generate=bool(auto_generate),
            ),
        )
        return {**preview, "applied": True, "id": str(created.id)}

    return preview


@tool(
    name="propose_update_recurring_transaction",
    description=_PROPOSAL_PREFACE
    + (
        "Build a preview for editing an existing recurring transaction "
        "(e.g. 'update my salary to R$8,000', 'change Netflix to R$60'). "
        "Pass the recurring_id and only the fields you want to change. "
        "Use auto_generate=false to stop Securo from auto-posting on the "
        "due date (reminder-only). auto_generate=true turns auto-post back on. "
        "Never send the user to the web app for this."
    ),
    parameters={
        "type": "object",
        "properties": {
            "recurring_id": {"type": "string", "format": "uuid"},
            "description": {"type": "string", "minLength": 1, "maxLength": 500},
            "amount": {"type": "number", "exclusiveMinimum": 0},
            "frequency": {"type": "string", "enum": ["weekly", "monthly", "quarterly", "yearly"]},
            "weekend_adjustment": {
                "type": "string",
                "enum": ["none", "previous_friday", "next_monday"],
            },
            "day_of_month": {"type": "integer", "minimum": 1, "maximum": 31},
            "end_date": {"type": "string", "format": "date"},
            "category_id": {"type": "string", "format": "uuid"},
            "is_active": {"type": "boolean"},
            "auto_generate": {
                "type": "boolean",
                "description": (
                    "false = reminder only (Orbit/user books). "
                    "true = Securo hourly job posts the due occurrence."
                ),
            },
            "apply": _APPLY_FIELD,
        },
        "required": ["recurring_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "recurring"],
)
async def propose_update_recurring_transaction(
    *,
    session: AsyncSession,
    ctx: CallContext,
    recurring_id: str,
    description: str | None = None,
    amount: float | None = None,
    frequency: str | None = None,
    weekend_adjustment: str | None = None,
    day_of_month: int | None = None,
    end_date: str | None = None,
    category_id: str | None = None,
    is_active: bool | None = None,
    auto_generate: bool | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    rid = parse_uuid(recurring_id)
    rt = (
        await session.execute(
            select(RecurringTransaction).where(
                RecurringTransaction.id == rid, RecurringTransaction.workspace_id == ws_id
            )
        )
    ).scalar_one_or_none()
    if rt is None:
        return {"error": "recurring transaction not found"}

    cat = None
    if category_id:
        cat = (
            await session.execute(
                select(Category).where(
                    Category.id == parse_uuid(category_id), Category.workspace_id == ws_id
                )
            )
        ).scalar_one_or_none()
        if cat is None:
            return {"error": "category not found"}

    changes: dict[str, Any] = {}
    if description is not None:
        changes["description"] = description.strip()
    if amount is not None:
        changes["amount"] = float(amount)
    if frequency is not None:
        changes["frequency"] = frequency
    if weekend_adjustment is not None:
        changes["weekend_adjustment"] = weekend_adjustment
    if day_of_month is not None:
        changes["day_of_month"] = int(day_of_month)
    if end_date is not None:
        parsed_end = parse_date(end_date)
        changes["end_date"] = parsed_end.isoformat() if parsed_end else None
    if cat is not None:
        changes["category_id"] = str(cat.id)
    if is_active is not None:
        changes["is_active"] = bool(is_active)
    if auto_generate is not None:
        changes["auto_generate"] = bool(auto_generate)

    if not changes:
        return {"error": "no changes provided"}

    preview = {
        "kind": "update_recurring_transaction",
        "target": {
            "id": str(rt.id),
            "description": rt.description,
            "amount": num(rt.amount),
            "currency": rt.currency,
            "frequency": rt.frequency,
            "weekend_adjustment": rt.weekend_adjustment,
            "day_of_month": rt.day_of_month,
            "is_active": bool(getattr(rt, "is_active", True)),
            "auto_generate": bool(getattr(rt, "auto_generate", True)),
        },
        "changes": changes,
        "apply_endpoint": f"PATCH /api/recurring-transactions/{rt.id}",
    }

    if _can_apply(ctx, apply):
        update_data: dict[str, Any] = {}
        if "description" in changes:
            update_data["description"] = changes["description"]
        if "amount" in changes:
            update_data["amount"] = Decimal(str(changes["amount"]))
        if "frequency" in changes:
            update_data["frequency"] = changes["frequency"]
        if "weekend_adjustment" in changes:
            update_data["weekend_adjustment"] = changes["weekend_adjustment"]
        if "day_of_month" in changes:
            update_data["day_of_month"] = changes["day_of_month"]
        if "end_date" in changes:
            update_data["end_date"] = (
                parse_date(changes["end_date"]) if changes["end_date"] else None
            )
        if "category_id" in changes:
            update_data["category_id"] = parse_uuid(changes["category_id"])
        if "is_active" in changes:
            update_data["is_active"] = changes["is_active"]
        if "auto_generate" in changes:
            update_data["auto_generate"] = changes["auto_generate"]
        updated = await recurring_transaction_service.update_recurring_transaction(
            session, rt.id, ws_id, RecurringTransactionUpdate(**update_data)
        )
        if updated is None:
            return {**preview, "error": "recurring transaction not found"}
        return {**preview, "applied": True, "id": str(updated.id)}

    return preview


@tool(
    name="propose_cancel_recurring_transaction",
    description=_PROPOSAL_PREFACE
    + (
        "Build a preview for cancelling a recurring transaction (e.g. "
        "'cancel that subscription'). Two modes: 'deactivate' keeps the "
        "history but stops future occurrences (recommended); 'delete' "
        "removes it entirely."
    ),
    parameters={
        "type": "object",
        "properties": {
            "recurring_id": {"type": "string", "format": "uuid"},
            "mode": {"type": "string", "enum": ["deactivate", "delete"], "default": "deactivate"},
            "apply": _APPLY_FIELD,
        },
        "required": ["recurring_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "recurring"],
)
async def propose_cancel_recurring_transaction(
    *,
    session: AsyncSession,
    ctx: CallContext,
    recurring_id: str,
    mode: str = "deactivate",
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    rt = (
        await session.execute(
            select(RecurringTransaction).where(
                RecurringTransaction.id == parse_uuid(recurring_id),
                RecurringTransaction.workspace_id == ws_id,
            )
        )
    ).scalar_one_or_none()
    if rt is None:
        return {"error": "recurring transaction not found"}

    if mode == "delete":
        endpoint = f"DELETE /api/recurring-transactions/{rt.id}"
    else:
        endpoint = f"PATCH /api/recurring-transactions/{rt.id}  body={{is_active: false}}"

    preview = {
        "kind": "cancel_recurring_transaction",
        "mode": mode,
        "target": {
            "id": str(rt.id),
            "description": rt.description,
            "amount": num(rt.amount),
            "currency": rt.currency,
            "frequency": rt.frequency,
            "is_active": bool(getattr(rt, "is_active", True)),
        },
        "apply_endpoint": endpoint,
    }

    if _can_apply(ctx, apply):
        if mode == "delete":
            ok = await recurring_transaction_service.delete_recurring_transaction(
                session, rt.id, ws_id
            )
            if not ok:
                return {**preview, "error": "recurring transaction not found"}
            return {**preview, "applied": True, "deleted": True}
        # deactivate path
        updated = await recurring_transaction_service.update_recurring_transaction(
            session, rt.id, ws_id, RecurringTransactionUpdate(is_active=False)
        )
        if updated is None:
            return {**preview, "error": "recurring transaction not found"}
        return {**preview, "applied": True, "id": str(updated.id), "is_active": False}

    return preview


@tool(
    name="propose_create_goal",
    description=_PROPOSAL_PREFACE
    + (
        "Build a preview for creating a savings/financial goal (e.g. "
        "'set a R$10k goal for travel')."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 255},
            "target_amount": {"type": "number", "exclusiveMinimum": 0},
            "currency": {"type": "string", "description": "Defaults to user's primary currency"},
            "deadline": {"type": "string", "format": "date"},
            "initial_amount": {
                "type": "number",
                "minimum": 0,
                "description": "How much you've already saved",
            },
            "icon": {"type": "string"},
            "color": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
            "apply": _APPLY_FIELD,
        },
        "required": ["name", "target_amount"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "goals"],
)
async def propose_create_goal(
    *,
    session: AsyncSession,
    ctx: CallContext,
    name: str,
    target_amount: float,
    currency: str | None = None,
    deadline: str | None = None,
    initial_amount: float | None = None,
    icon: str | None = None,
    color: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    resolved_currency = (currency or "BRL").upper()
    resolved_deadline = parse_date(deadline) if deadline else None
    resolved_initial = float(initial_amount) if initial_amount is not None else 0.0
    preview = {
        "kind": "create_goal",
        "proposed": {
            "name": name.strip(),
            "target_amount": float(target_amount),
            "currency": resolved_currency,
            "deadline": resolved_deadline.isoformat() if resolved_deadline else None,
            "initial_amount": resolved_initial,
            "icon": icon or "target",
            "color": color or "#3B82F6",
        },
        "apply_endpoint": "POST /api/goals",
    }

    if _can_apply(ctx, apply):
        ws_id = await resolve_workspace_id(session, ctx)
        created = await goal_service.create_goal(
            session,
            ws_id,
            ctx.user_id,
            GoalCreate(
                name=name.strip(),
                target_amount=Decimal(str(target_amount)),
                current_amount=Decimal(str(resolved_initial)),
                currency=resolved_currency,
                target_date=resolved_deadline,
                icon=icon or "target",
                color=color or "#3B82F6",
            ),
        )
        return {**preview, "applied": True, "id": str(created.id)}

    return preview


def _today():
    from datetime import date as _d

    return _d.today()


@tool(
    name="propose_create_payee_rule",
    description=_PROPOSAL_PREFACE
    + (
        "Preview a rule that auto-categorizes future transactions matching "
        "a description pattern. Returns the proposed rule shape."
    ),
    parameters={
        "type": "object",
        "properties": {
            "match_pattern": {
                "type": "string",
                "description": "Substring to match in transaction description (case-insensitive)",
            },
            "category_id": {"type": "string", "format": "uuid"},
            "apply": _APPLY_FIELD,
        },
        "required": ["match_pattern", "category_id"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "rules"],
)
async def propose_create_payee_rule(
    *,
    session: AsyncSession,
    ctx: CallContext,
    match_pattern: str,
    category_id: str,
    apply: bool = False,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    cat_id = parse_uuid(category_id)
    cat = (
        await session.execute(
            select(Category).where(Category.id == cat_id, Category.workspace_id == ws_id)
        )
    ).scalar_one_or_none()
    if cat is None:
        return {"error": "category not found"}

    preview = {
        "kind": "create_payee_rule",
        "proposed": {
            "match_pattern": match_pattern,
            "category_id": str(cat.id),
            "category_name": cat.name,
        },
        "apply_endpoint": "POST /api/rules",
    }

    if _can_apply(ctx, apply):
        created = await rule_service.create_rule(
            session,
            ws_id,
            ctx.user_id,
            RuleCreate(
                name=f"Auto-categorize: {match_pattern}",
                conditions_op="and",
                conditions=[RuleCondition(field="description", op="contains", value=match_pattern)],
                actions=[RuleAction(op="set_category", value=str(cat.id))],
            ),
        )
        return {**preview, "applied": True, "id": str(created.id)}

    return preview
