#!/usr/bin/env python3
"""Enrich ICICI Commercial as NRP loan TBPUN00006895113 (Godrej Emerald Waters).

Idempotent data seed — does NOT create a second loan (would double-count BS).
- Labels/notes on display_name + external_id
- Mark 33 EMIs paid; regenerate remaining 130 from live OS @ 7.75%
- Align recurring EMI debit on ICICI savings (auto-debit 003901608757)
- Leave Pru policy loan untouched
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.account import Account
from app.models.loan_schedule import LoanAmortizationSchedule
from app.models.recurring_transaction import RecurringTransaction
from app.schemas.recurring_transaction import RecurringTransactionCreate
from app.services import loan_schedule_service, recurring_transaction_service

LOAN_ID = uuid.UUID("2586addb-6f3a-4693-b1bd-675ac08694e0")
PRU_ID = uuid.UUID("0b712d44-c283-4144-a958-318db59f0236")
SAVINGS_ID = uuid.UUID("fccfbc47-1ac7-4e5b-a9be-3a0607f923f4")
EMI_CATEGORY_ID = uuid.UUID("79451106-9ebb-44bc-97aa-f8005a2ef6aa")
EXISTING_REC_ID = uuid.UUID("75e260ee-bfdc-48ce-8537-cd81f0f16a81")

ACCOUNT_NO = "TBPUN00006895113"
OS_PRINCIPAL = Decimal("10669593.00")
EMI_AMOUNT = Decimal("121543.00")
RATE = Decimal("7.7500")
PAID_COUNT = 33
PENDING_COUNT = 130
ACCRUED_INTEREST = Decimal("18375.00")
AS_OF = date(2026, 9, 13)
DISBURSED = date(2023, 11, 28)

# Chips + KM notes (≤255 chars for display_name)
DISPLAY_NAME = (
    "ICICI NRP · 7.75% float · EMI ₹1,21,543 · tenor left 130 | "
    "Godrej Emerald Waters U114 Chinchwad (NOT Nexus) | TBPUN…5113 | "
    "Co-app Prerna | Rate 9→8.5→8→7.75 | Accrued≈₹18.4k@13-Sep | "
    "Stack NRP EMI+Pru before surplus"
)

REC_DESC = "ICICI NRP EMI — Godrej Emerald Waters U114 (TBPUN…5113)"

OUT = Path(__file__).resolve().parent / "seed_nrp_tbpun_result.json"


async def main() -> dict:
    assert len(DISPLAY_NAME) <= 255, f"display_name too long: {len(DISPLAY_NAME)}"

    async with async_session_maker() as session:
        loan = await session.get(Account, LOAN_ID)
        pru = await session.get(Account, PRU_ID)
        savings = await session.get(Account, SAVINGS_ID)
        if not loan or loan.type != "loan":
            raise SystemExit(f"Loan {LOAN_ID} not found")
        if not pru or pru.type != "loan":
            raise SystemExit(f"Pru loan missing — abort to avoid collateral damage")
        if not savings:
            raise SystemExit(f"Savings {SAVINGS_ID} not found")

        pru_name_before = pru.name
        pru_bal_before = pru.balance

        # --- 1) Account enrichment (keep name 'ICICI Commercial' for continuity) ---
        loan.display_name = DISPLAY_NAME
        loan.external_id = ACCOUNT_NO
        loan.masked_number = ACCOUNT_NO[-4:]
        loan.disbursed_on = DISBURSED
        loan.interest_rate = RATE
        loan.emi_amount = EMI_AMOUNT
        loan.original_principal = Decimal("11746500.00")
        loan.tenure_months = PAID_COUNT + PENDING_COUNT  # 163
        loan.emi_day = 5
        loan.balance = OS_PRINCIPAL
        loan.loan_kind = "home"  # property; NRP product called out in display_name
        # Tag savings auto-debit account last-4 if empty
        if not savings.masked_number:
            savings.masked_number = "8757"
        if not savings.external_id:
            savings.external_id = "003901608757"

        await session.commit()
        await session.refresh(loan)

        # --- 2) Mark EMIs 1..33 paid on current version ---
        version = loan.current_schedule_version or 1
        result = await session.execute(
            select(LoanAmortizationSchedule)
            .where(
                LoanAmortizationSchedule.account_id == LOAN_ID,
                LoanAmortizationSchedule.schedule_version == version,
            )
            .order_by(LoanAmortizationSchedule.emi_number)
        )
        entries = list(result.scalars().all())
        if not entries:
            entries = await loan_schedule_service.generate_amortization_schedule(
                session, LOAN_ID, version=1
            )
            version = 1

        marked = 0
        for e in entries:
            if e.emi_number <= PAID_COUNT and e.payment_status != "paid":
                e.payment_status = "paid"
                e.actual_payment_date = e.due_date
                e.actual_amount_paid = e.emi_amount
                e.notes = (e.notes or "")[:900]
                if e.emi_number == PAID_COUNT:
                    e.notes = (
                        f"Paid through EMI#{PAID_COUNT} (as-of {AS_OF.isoformat()}). "
                        f"Historical path used bank OS anchor; rate hist 9.0→8.5→8.0→7.75."
                    )[:1000]
                marked += 1
        await session.commit()

        # --- 3) Regenerate from EMI 34 with live OS @ current rate, 130 months ---
        from_emi = PAID_COUNT + 1
        new_entries = await loan_schedule_service.regenerate_schedule(
            session,
            LOAN_ID,
            from_emi_number=from_emi,
            new_params={
                "new_principal_balance": OS_PRINCIPAL,
                "new_interest_rate": RATE,
                "new_tenure_months": PENDING_COUNT,
                "new_emi_amount": EMI_AMOUNT,
            },
        )
        if new_entries:
            new_entries[0].notes = (
                f"NRP schedule reset @ {RATE}% from OS ₹{OS_PRINCIPAL} "
                f"(accrued int ₹{ACCRUED_INTEREST} as-of {AS_OF}). "
                f"Property: Unit 114 Godrej Emerald Waters (Commercial), Chinchwad — NOT Nexus. "
                f"Co-applicant: Prerna Mayur Kharche. Acct {ACCOUNT_NO}."
            )[:1000]
            await session.commit()

        await session.refresh(loan)
        # Re-assert live OS (regenerate must not drift balance via sync)
        loan.balance = OS_PRINCIPAL
        loan.emi_amount = EMI_AMOUNT
        loan.interest_rate = RATE
        await session.commit()

        # --- 4) Recurring EMI on ICICI savings ---
        rec = await session.get(RecurringTransaction, EXISTING_REC_ID)
        created_rec = False
        if rec:
            rec.description = REC_DESC
            rec.amount = EMI_AMOUNT
            rec.amount_primary = EMI_AMOUNT
            rec.currency = "INR"
            rec.type = "debit"
            rec.frequency = "monthly"
            rec.day_of_month = 5
            rec.account_id = SAVINGS_ID
            rec.category_id = EMI_CATEGORY_ID
            rec.is_active = True
            rec.auto_generate = False
            if rec.next_occurrence and rec.next_occurrence < AS_OF:
                rec.next_occurrence = date(2026, 10, 5)
            await session.commit()
            await session.refresh(rec)
        else:
            # fallback create
            rec, created_rec = await _ensure_recurring(
                session,
                loan.workspace_id,
                loan.user_id,
                RecurringTransactionCreate(
                    description=REC_DESC,
                    amount=EMI_AMOUNT,
                    currency="INR",
                    type="debit",
                    frequency="monthly",
                    day_of_month=5,
                    start_date=date(2026, 10, 5),
                    account_id=SAVINGS_ID,
                    category_id=EMI_CATEGORY_ID,
                    auto_generate=False,
                ),
            )

        # --- 5) Verify counts + Pru untouched ---
        await session.refresh(loan)
        await session.refresh(pru)
        cur_ver = loan.current_schedule_version
        result = await session.execute(
            select(LoanAmortizationSchedule)
            .where(
                LoanAmortizationSchedule.account_id == LOAN_ID,
                LoanAmortizationSchedule.schedule_version == cur_ver,
            )
            .order_by(LoanAmortizationSchedule.emi_number)
        )
        sched = list(result.scalars().all())
        paid = [e for e in sched if e.payment_status == "paid"]
        pending = [e for e in sched if e.payment_status == "scheduled"]
        future_emi_sum = sum((e.emi_amount for e in pending), Decimal("0"))

        if pru.name != pru_name_before or pru.balance != pru_bal_before:
            raise SystemExit("Pru loan mutated — abort")

        overview_paid = len(paid)
        overview_pending = len(pending)

        result_payload = {
            "loan_id": str(LOAN_ID),
            "name": loan.name,
            "display_name": loan.display_name,
            "external_id": loan.external_id,
            "masked_number": loan.masked_number,
            "balance": str(loan.balance),
            "emi_amount": str(loan.emi_amount),
            "interest_rate": str(loan.interest_rate),
            "tenure_months": loan.tenure_months,
            "disbursed_on": loan.disbursed_on.isoformat() if loan.disbursed_on else None,
            "schedule_version": cur_ver,
            "schedule_total": len(sched),
            "paid": overview_paid,
            "pending": overview_pending,
            "marked_this_run": marked,
            "regenerated_future": len(new_entries),
            "future_instalments_sum": str(future_emi_sum),
            "accrued_interest_note": str(ACCRUED_INTEREST),
            "recurring_id": str(rec.id),
            "recurring_description": rec.description,
            "recurring_amount": str(rec.amount),
            "recurring_created": created_rec,
            "savings_id": str(SAVINGS_ID),
            "savings_external_id": savings.external_id,
            "pru_untouched": True,
            "money_loan_url": f"https://money.planetfinance.cloud/loans/{LOAN_ID}",
            "as_of": AS_OF.isoformat(),
            "seeded_at": datetime.now(timezone.utc).isoformat(),
        }
        OUT.write_text(json.dumps(result_payload, indent=2))
        print(json.dumps(result_payload, indent=2))
        return result_payload


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
        existing.is_active = True
        existing.category_id = data.category_id or existing.category_id
        await session.commit()
        await session.refresh(existing)
        return existing, False
    created = await recurring_transaction_service.create_recurring_transaction(
        session, workspace_id, user_id, data
    )
    return created, True


if __name__ == "__main__":
    asyncio.run(main())
