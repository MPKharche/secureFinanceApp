"""Guided post-on-due for reminder-only recurring bills (G0 dual-ledger).

Creates real ledger rows (and optional savings→loan transfer) then advances the
recurring pointer — safer than blind auto_generate for policy premium/interest.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.asset import Asset
from app.models.loan_schedule import LoanAmortizationSchedule
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.schemas.transaction import TransferCreate
from app.services import recurring_match_service
from app.services.credit_card_service import apply_effective_date
from app.services.g0_assumption_keys import amount_from_g0_assumption, assumption_refs_from_g0
from app.services.recurring_transaction_service import adjust_weekend_date
from app.services import transaction_service


class ScheduledPostError(ValueError):
    """User-visible validation failure for guided posting."""


async def _load_g0_for_recurring(
    session: AsyncSession, workspace_id: uuid.UUID, recurring_id: uuid.UUID
) -> tuple[Optional[dict[str, Any]], Optional[Asset]]:
    result = await session.execute(select(Asset).where(Asset.workspace_id == workspace_id))
    rid = str(recurring_id)
    for asset in result.scalars().all():
        g0 = (asset.external_metadata or {}).get("g0_assumptions") or {}
        if rid in (
            g0.get("linked_premium_recurring_id"),
            g0.get("linked_interest_recurring_id"),
            g0.get("linked_repayment_recurring_id"),
        ):
            return g0, asset
    return None, None


def _post_kind_from_g0(g0: Optional[dict], recurring_id: uuid.UUID) -> str:
    if not g0:
        return "generic"
    rid = str(recurring_id)
    if g0.get("linked_premium_recurring_id") == rid:
        return "premium"
    if g0.get("linked_interest_recurring_id") == rid:
        return "interest_half_yearly"
    if g0.get("linked_repayment_recurring_id") == rid:
        return "principal_repayment"
    return "generic"


async def _existing_occurrence_tx(
    session: AsyncSession,
    recurring_id: uuid.UUID,
    effective_date: date,
    window_days: int = 7,
) -> Optional[Transaction]:
    lo = effective_date - timedelta(days=window_days)
    hi = effective_date + timedelta(days=window_days)
    result = await session.execute(
        select(Transaction).where(
            Transaction.recurring_transaction_id == recurring_id,
            Transaction.date >= lo,
            Transaction.date <= hi,
        )
    )
    rows = list(result.scalars().all())
    return rows[0] if rows else None


async def _find_schedule_entry(
    session: AsyncSession,
    loan_account_id: uuid.UUID,
    *,
    due_near: date,
    amount: Decimal,
    interest_only: bool = True,
) -> Optional[LoanAmortizationSchedule]:
    result = await session.execute(
        select(Account.current_schedule_version).where(Account.id == loan_account_id)
    )
    version = result.scalar_one_or_none()
    if version is None:
        return None

    result = await session.execute(
        select(LoanAmortizationSchedule).where(
            LoanAmortizationSchedule.account_id == loan_account_id,
            LoanAmortizationSchedule.schedule_version == version,
            LoanAmortizationSchedule.payment_status == "scheduled",
            LoanAmortizationSchedule.due_date >= due_near - timedelta(days=14),
            LoanAmortizationSchedule.due_date <= due_near + timedelta(days=14),
        )
    )
    candidates = list(result.scalars().all())
    amount_q = amount.quantize(Decimal("0.01"))
    for entry in candidates:
        emi_q = entry.emi_amount.quantize(Decimal("0.01"))
        if emi_q != amount_q:
            continue
        if interest_only and entry.principal_component != Decimal("0.00"):
            continue
        if not interest_only and entry.principal_component == Decimal("0.00"):
            continue
        return entry
    return None


async def _stamp_recurring_on_transfer_debit(
    session: AsyncSession,
    debit_tx: Transaction,
    recurring: RecurringTransaction,
    g0: Optional[dict],
    kind: str,
) -> None:
    debit_tx.recurring_transaction_id = recurring.id
    if recurring.category_id:
        debit_tx.category_id = recurring.category_id
    refs = assumption_refs_from_g0(g0)
    debit_tx.raw_data = {
        **(debit_tx.raw_data or {}),
        "kind": "g0_scheduled_post",
        "post_kind": kind,
        "assumption_refs": refs,
    }


async def post_recurring_occurrence(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    recurring_id: uuid.UUID,
    *,
    payment_date: Optional[date] = None,
    transfer_to_account_id: Optional[uuid.UUID] = None,
    link_loan_schedule: bool = False,
    loan_account_id: Optional[uuid.UUID] = None,
) -> dict:
    """Materialize one due occurrence for a reminder-only recurring bill."""
    result = await session.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.id == recurring_id,
            RecurringTransaction.workspace_id == workspace_id,
        )
    )
    recurring = result.scalar_one_or_none()
    if not recurring:
        raise ScheduledPostError("Recurring transaction not found")
    if not recurring.is_active:
        raise ScheduledPostError("Recurring bill is inactive")
    if recurring.account_id is None:
        raise ScheduledPostError("Recurring bill has no account")

    g0, _asset = await _load_g0_for_recurring(session, workspace_id, recurring_id)
    kind = _post_kind_from_g0(g0, recurring_id)

    nominal = recurring.next_occurrence
    effective = payment_date or adjust_weekend_date(nominal, recurring.weekend_adjustment)

    today = date.today()
    if effective > today + timedelta(days=3):
        raise ScheduledPostError(
            "Occurrence is not due yet — post on or within 3 days after the due date"
        )

    existing = await _existing_occurrence_tx(session, recurring.id, effective)
    if existing:
        return {
            "already_posted": True,
            "transaction_ids": [str(existing.id)],
            "recurring_id": str(recurring.id),
            "next_occurrence": recurring.next_occurrence,
        }

    amount = amount_from_g0_assumption(g0, kind=kind, fallback=recurring.amount)
    if amount != recurring.amount:
        recurring.amount = amount

    if g0 and not transfer_to_account_id:
        loan_hint = g0.get("loan_account_id")
        if loan_hint and kind in ("interest_half_yearly", "principal_repayment"):
            transfer_to_account_id = uuid.UUID(str(loan_hint))
            link_loan_schedule = True
            loan_account_id = transfer_to_account_id

    if loan_account_id is None and transfer_to_account_id is not None:
        loan_account_id = transfer_to_account_id

    cash_leg: Transaction
    credit_leg: Optional[Transaction] = None

    if transfer_to_account_id is not None:
        if transfer_to_account_id == recurring.account_id:
            raise ScheduledPostError("Transfer destination must differ from cash account")
        transfer = TransferCreate(
            from_account_id=recurring.account_id,
            to_account_id=transfer_to_account_id,
            amount=amount,
            date=effective,
            description=recurring.description,
            notes="G0 guided post: savings→loan for O/S coherence",
        )
        cash_leg, credit_leg = await transaction_service.create_transfer(
            session, workspace_id, user_id, transfer
        )
        await _stamp_recurring_on_transfer_debit(session, cash_leg, recurring, g0, kind)
        if credit_leg.raw_data is None:
            credit_leg.raw_data = {}
        credit_leg.raw_data = {
            **credit_leg.raw_data,
            "kind": "g0_scheduled_post",
            "post_kind": kind,
            "assumption_refs": assumption_refs_from_g0(g0),
            "paired_cash_leg_id": str(cash_leg.id),
        }
        await session.commit()
        await session.refresh(cash_leg)
        await session.refresh(credit_leg)
    else:
        if recurring.type != "debit":
            raise ScheduledPostError("Cash expense post supports debit recurrings only")
        from app.schemas.transaction import TransactionCreate

        cash_leg = await transaction_service.create_transaction(
            session,
            workspace_id,
            user_id,
            TransactionCreate(
                account_id=recurring.account_id,
                category_id=recurring.category_id,
                description=recurring.description,
                amount=amount,
                currency=recurring.currency,
                date=effective,
                type="debit",
                status="posted",
                notes="G0 guided post: premium/expense",
            ),
        )
        cash_leg.source = "scheduled_post"
        cash_leg.recurring_transaction_id = recurring.id
        cash_leg.raw_data = {
            "kind": "g0_scheduled_post",
            "post_kind": kind,
            "assumption_refs": assumption_refs_from_g0(g0),
        }
        await session.commit()
        await session.refresh(cash_leg)

    schedule_entry_id: Optional[str] = None
    if link_loan_schedule and loan_account_id:
        interest_only = kind != "principal_repayment"
        entry = await _find_schedule_entry(
            session,
            loan_account_id,
            due_near=effective,
            amount=amount,
            interest_only=interest_only,
        )
        if entry is None and nominal != effective:
            entry = await _find_schedule_entry(
                session,
                loan_account_id,
                due_near=nominal,
                amount=amount,
                interest_only=interest_only,
            )
        if entry:
            entry.payment_status = "paid"
            entry.actual_payment_date = effective
            entry.actual_amount_paid = amount
            entry.linked_transaction_id = cash_leg.id
            entry.linked_transaction_ids = str(cash_leg.id)
            schedule_entry_id = str(entry.id)
            await session.commit()

    recurring_match_service.advance_past(recurring, effective)
    await session.commit()
    await session.refresh(recurring)

    tx_ids = [str(cash_leg.id)]
    if credit_leg:
        tx_ids.append(str(credit_leg.id))

    return {
        "already_posted": False,
        "transaction_ids": tx_ids,
        "cash_leg_id": str(cash_leg.id),
        "credit_leg_id": str(credit_leg.id) if credit_leg else None,
        "schedule_entry_id": schedule_entry_id,
        "recurring_id": str(recurring.id),
        "next_occurrence": recurring.next_occurrence.isoformat(),
        "post_kind": kind,
    }


async def post_loan_schedule_payment(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    *,
    from_account_id: uuid.UUID,
    payment_date: Optional[date] = None,
) -> dict:
    """Post a scheduled loan row as savings→loan transfer and link the cash leg."""
    result = await session.execute(
        select(LoanAmortizationSchedule).where(LoanAmortizationSchedule.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry or entry.workspace_id != workspace_id:
        raise ScheduledPostError("Schedule entry not found")
    if entry.payment_status == "paid":
        raise ScheduledPostError("Schedule entry is already paid")

    pay_date = payment_date or entry.due_date
    amount = entry.emi_amount

    transfer = TransferCreate(
        from_account_id=from_account_id,
        to_account_id=entry.account_id,
        amount=amount,
        date=pay_date,
        description=f"Loan payment · EMI #{entry.emi_number}",
        notes=entry.notes or "Guided schedule post",
    )
    cash_leg, credit_leg = await transaction_service.create_transfer(
        session, workspace_id, user_id, transfer
    )
    entry.payment_status = "paid"
    entry.actual_payment_date = pay_date
    entry.actual_amount_paid = amount
    entry.linked_transaction_id = cash_leg.id
    entry.linked_transaction_ids = str(cash_leg.id)
    cash_leg.raw_data = {
        **(cash_leg.raw_data or {}),
        "kind": "g0_schedule_post",
        "loan_schedule_entry_id": str(entry.id),
    }
    recurring_advanced: Optional[str] = None

    # Try to advance matching G0 recurring from asset metadata
    result_assets = await session.execute(select(Asset).where(Asset.workspace_id == workspace_id))
    for asset in result_assets.scalars().all():
        g0 = (asset.external_metadata or {}).get("g0_assumptions") or {}
        loan_hint = g0.get("loan_account_id")
        if loan_hint and str(entry.account_id) != str(loan_hint):
            continue
        linked_rid: Optional[str]
        if entry.principal_component == Decimal("0.00"):
            linked_rid = g0.get("linked_interest_recurring_id")
        else:
            linked_rid = g0.get("linked_repayment_recurring_id")
        if not linked_rid:
            continue
        rec_result = await session.execute(
            select(RecurringTransaction).where(
                RecurringTransaction.id == uuid.UUID(str(linked_rid)),
                RecurringTransaction.workspace_id == workspace_id,
            )
        )
        rec = rec_result.scalar_one_or_none()
        if rec:
            cash_leg.recurring_transaction_id = rec.id
            recurring_match_service.advance_past(rec, pay_date)
            recurring_advanced = str(rec.id)
        break

    await session.commit()

    return {
        "transaction_ids": [str(cash_leg.id), str(credit_leg.id)],
        "schedule_entry_id": str(entry.id),
        "recurring_id": recurring_advanced,
    }
