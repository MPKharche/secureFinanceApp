#!/usr/bin/env python3
"""Seed ICICI Pru A8884526 premium + half-yearly interest schedules (G0).

Idempotent: skips creating recurrings that already match description+account.
Regenerates loan amortization as interest-only half-yearly + principal stub.
Stores G4-lite assumption keys on asset.external_metadata and goal.metadata_json.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# Allow running inside backend container or from repo with PYTHONPATH=backend
BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import AsyncSessionLocal
from app.models.account import Account
from app.models.asset import Asset
from app.models.category import Category
from app.models.goal import Goal
from app.models.recurring_transaction import RecurringTransaction
from app.schemas.recurring_transaction import RecurringTransactionCreate
from app.services import loan_schedule_service, recurring_transaction_service

LOAN_ID = uuid.UUID("0b712d44-c283-4144-a958-318db59f0236")
ASSET_ID = uuid.UUID("ad85ba9f-69a3-4423-b3f4-d2b896ed1b7f")
GOAL_ID = uuid.UUID("bd8297cc-5a74-4c6d-8ea0-23cfbd47f949")
SAVINGS_ID = uuid.UUID("fccfbc47-1ac7-4e5b-a9be-3a0607f923f4")

PREMIUM_DESC = "ICICI Pru GIFT A8884526 Premium"
INTEREST_DESC = "ICICI Pru Policy Loan A8884526 Interest"
REPAY_DESC = "ICICI Pru Policy Loan A8884526 Principal repayment stub"

PREMIUM_AMOUNT = Decimal("10000.00")
RATE = Decimal("7.96")
PRINCIPAL = Decimal("160000.00")
HALF_YEAR_INTEREST = (PRINCIPAL * RATE / Decimal("100") / Decimal("2")).quantize(
    Decimal("0.01"), rounding=ROUND_HALF_UP
)


async def _find_category(session, workspace_id, names: list[str]):
    result = await session.execute(
        select(Category).where(Category.workspace_id == workspace_id)
    )
    cats = list(result.scalars().all())
    lower = {c.name.lower(): c for c in cats}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


async def _ensure_recurring(session, workspace_id, user_id, data: RecurringTransactionCreate):
    result = await session.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.workspace_id == workspace_id,
            RecurringTransaction.description == data.description,
            RecurringTransaction.account_id == data.account_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.amount = data.amount
        existing.frequency = data.frequency
        existing.day_of_month = data.day_of_month
        existing.currency = data.currency
        existing.type = data.type
        existing.is_active = True
        existing.auto_generate = data.auto_generate
        existing.category_id = data.category_id or existing.category_id
        await session.commit()
        await session.refresh(existing)
        return existing, False
    created = await recurring_transaction_service.create_recurring_transaction(
        session, workspace_id, user_id, data
    )
    return created, True


async def main() -> dict:
    async with AsyncSessionLocal() as session:
        loan = await session.get(Account, LOAN_ID)
        if not loan or loan.type != "loan":
            raise SystemExit(f"Loan {LOAN_ID} not found")
        asset = await session.get(Asset, ASSET_ID)
        goal = await session.get(Goal, GOAL_ID)
        savings = await session.get(Account, SAVINGS_ID)
        if not savings:
            raise SystemExit(f"Savings {SAVINGS_ID} not found")

        workspace_id = loan.workspace_id
        user_id = loan.user_id

        # 1) Interest-only half-yearly loan schedule + principal balloon stub
        entries = await loan_schedule_service.generate_interest_only_schedule(
            session,
            LOAN_ID,
            cadence_months=6,
            include_principal_balloon=True,
        )

        emi_cat = await _find_category(session, workspace_id, ["EMI / Loans", "Loans", "Interest"])
        insur_cat = await _find_category(
            session, workspace_id, ["Insurance", "Insurance Premium", "Life Insurance"]
        )

        # 2) Premium monthly on cash (reminder-only by default — bank/UPI is source of truth)
        premium, premium_created = await _ensure_recurring(
            session,
            workspace_id,
            user_id,
            RecurringTransactionCreate(
                description=PREMIUM_DESC,
                amount=PREMIUM_AMOUNT,
                currency="INR",
                type="debit",
                frequency="monthly",
                day_of_month=17,  # policy start ~17 Nov cadence
                start_date=date(2026, 9, 17),
                account_id=SAVINGS_ID,
                category_id=insur_cat.id if insur_cat else None,
                auto_generate=False,
            ),
        )

        # 3) Half-yearly interest charge on cash (reminder). Paying via transfer
        # savings→loan credits the loan and keeps O/S coherent with current_balance.
        interest, interest_created = await _ensure_recurring(
            session,
            workspace_id,
            user_id,
            RecurringTransactionCreate(
                description=INTEREST_DESC,
                amount=HALF_YEAR_INTEREST,
                currency="INR",
                type="debit",
                frequency="semiannual",
                day_of_month=25,
                start_date=date(2026, 3, 25),
                account_id=SAVINGS_ID,
                category_id=emi_cat.id if emi_cat else None,
                auto_generate=False,
            ),
        )

        # 4) Optional principal repayment stub (inactive template until user enables)
        repay, repay_created = await _ensure_recurring(
            session,
            workspace_id,
            user_id,
            RecurringTransactionCreate(
                description=REPAY_DESC,
                amount=PRINCIPAL,
                currency="INR",
                type="debit",
                frequency="yearly",
                day_of_month=18,
                start_date=date(2026, 5, 18),
                end_date=date(2026, 5, 18),
                account_id=SAVINGS_ID,
                category_id=emi_cat.id if emi_cat else None,
                auto_generate=False,
            ),
        )
        # Keep stub inactive until user decides to repay
        repay.is_active = False
        await session.commit()

        assumptions = {
            "premium_amount": float(PREMIUM_AMOUNT),
            "loan_rate_percent": float(RATE),
            "interest_cadence": "half_yearly",
            "interest_amount_half_yearly": float(HALF_YEAR_INTEREST),
            "principal": float(PRINCIPAL),
            "sv_source": "CoS benefit illustration in policy PDF — NOT live ICICI quote",
            "linked_premium_recurring_id": str(premium.id),
            "linked_interest_recurring_id": str(interest.id),
            "linked_repayment_recurring_id": str(repay.id),
            "loan_schedule_version": entries[0].schedule_version if entries else None,
            "coherence_notes": (
                "Celery generate-recurring-daily materializes auto_generate=true bills. "
                "These Pru templates are reminder-only (auto_generate=false). "
                "Pay interest as transfer savings→loan so loan current_balance drops; "
                "mark matching loan schedule interest row paid and link the cash leg."
            ),
        }

        if asset is not None:
            meta = dict(asset.external_metadata or {})
            meta["g0_assumptions"] = assumptions
            meta["premium_monthly"] = float(PREMIUM_AMOUNT)
            meta["linked_premium_recurring_id"] = str(premium.id)
            meta["linked_interest_recurring_id"] = str(interest.id)
            asset.external_metadata = meta
            asset.sip_amount = PREMIUM_AMOUNT
            asset.sip_day = 17
            flag_modified(asset, "external_metadata")

        if goal is not None:
            gmeta = dict(goal.metadata_json or {})
            gmeta["g0_assumptions"] = assumptions
            gmeta["interest_cadence"] = "half_yearly"
            gmeta["rate_percent"] = float(RATE)
            goal.metadata_json = gmeta
            flag_modified(goal, "metadata_json")

        await session.commit()

        out = {
            "loan_id": str(LOAN_ID),
            "schedule_entries": len(entries),
            "schedule_version": entries[0].schedule_version if entries else None,
            "half_year_interest": str(HALF_YEAR_INTEREST),
            "premium_recurring_id": str(premium.id),
            "premium_created": premium_created,
            "interest_recurring_id": str(interest.id),
            "interest_created": interest_created,
            "repayment_recurring_id": str(repay.id),
            "repayment_created": repay_created,
            "assumptions": assumptions,
        }
        print(json.dumps(out, indent=2))
        return out


if __name__ == "__main__":
    asyncio.run(main())
