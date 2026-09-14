#!/usr/bin/env python3
"""Enrich ICICI Commercial as NRP loan TBPUN00006895113 (Godrej Emerald Waters).

Idempotent data seed — does NOT create a second loan (would double-count BS).

Schedule is rebuilt from the ICICI statement (as-of 13-Sep-2026):
  - 5 phased disbursals (Nov-23 → May-26), NOT full draw at sanction
  - Pre-EMI Dec-23 ₹3,599 (broken period; not counted in 33 instalments)
  - Partial/stepped EMIs until full draw; full EMI ₹1,21,543 from May-26
  - Rate path 9.0 → 8.5 → 8.0 → 7.75
  - Paid 33 / pending 130; OS principal ₹1,06,69,593

myKnowledgeManager assumption chips (baked into display_name + schedule notes)
so future regenerates do NOT flatten to full EMI from sanction:
  disbursal_phases=5 | pre_emi/partial_emi→full@May-26 | rate_path=9→8.5→8→7.75
  projections=actual_cash_to_asof_then_current_EMI_forward

Leave Pru policy loan untouched.
"""
from __future__ import annotations

import asyncio
import calendar
import json
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
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
PRE_EMI = (date(2023, 12, 5), Decimal("3599.00"))

# Statement disbursals (5 phases) — total ₹1,17,46,500
DISBURSALS: list[tuple[date, Decimal]] = [
    (date(2023, 11, 30), Decimal("2878713.00")),
    (date(2024, 5, 21), Decimal("2918813.00")),
    (date(2024, 7, 15), Decimal("2889913.00")),
    (date(2025, 3, 24), Decimal("1767435.00")),
    (date(2026, 5, 4), Decimal("1291626.00")),
]

# Rate path (statement Pre-Payment/Conversion Details)
RATE_PATH: list[tuple[date, Decimal]] = [
    (date(2023, 11, 28), Decimal("9.00")),
    (date(2024, 2, 1), Decimal("9.00")),
    (date(2025, 5, 1), Decimal("8.50")),
    (date(2025, 8, 1), Decimal("8.00")),
    (date(2026, 2, 1), Decimal("7.75")),
]

# Statement EMI cash history (Inst.1 Jan-24 … Inst.33 Sep-26). Full EMI from Inst.29.
EMI_BLOCKS: list[tuple[int, int, Decimal, date]] = [
    (1, 5, Decimal("29198.00"), date(2024, 1, 5)),
    (6, 7, Decimal("59086.00"), date(2024, 6, 5)),
    (8, 15, Decimal("88889.00"), date(2024, 8, 5)),
    (16, 28, Decimal("107509.00"), date(2025, 4, 5)),
    (29, 33, Decimal("121543.00"), date(2026, 5, 5)),  # first full EMI after final draw
]

FIRST_FULL_EMI_DATE = date(2026, 5, 5)

# Chips ≤255 — KM assumptions baked so regenerate agents don't flatten
DISPLAY_NAME = (
    "ICICI NRP · 7.75% · EMI ₹1,21,543 · tenor 130 | "
    "KM:disbursal_phases=5;pre_emi/partial→full@May-26;rate_path=9→8.5→8→7.75;"
    "proj=cash_hist→current_EMI | Godrej U114 | TBPUN…5113 | OS₹1.07Cr@13-Sep"
)

KM_ASSUMPTIONS = {
    "disbursal_phases": [
        {"date": d.isoformat(), "amount": str(a)} for d, a in DISBURSALS
    ],
    "pre_emi": {"date": PRE_EMI[0].isoformat(), "amount": str(PRE_EMI[1])},
    "partial_emi_until": FIRST_FULL_EMI_DATE.isoformat(),
    "full_emi": str(EMI_AMOUNT),
    "first_full_emi_date": FIRST_FULL_EMI_DATE.isoformat(),
    "rate_path": [{"eff": d.isoformat(), "rate": str(r)} for d, r in RATE_PATH],
    "projections": "actual_cash_history_to_asof_then_current_EMI_forward",
    "do_not_flatten": True,
    "statement_as_of": AS_OF.isoformat(),
    "os_principal": str(OS_PRINCIPAL),
    "paid": PAID_COUNT,
    "pending": PENDING_COUNT,
}

REC_DESC = "ICICI NRP EMI — Godrej Emerald Waters U114 (TBPUN…5113)"
OUT = Path(__file__).resolve().parent / "seed_nrp_tbpun_result.json"


def _add_months(d: date, m: int) -> date:
    y = d.year + (d.month - 1 + m) // 12
    mo = (d.month - 1 + m) % 12 + 1
    day = min(d.day, calendar.monthrange(y, mo)[1])
    return date(y, mo, day)


def _rate_on(d: date) -> Decimal:
    rate = RATE_PATH[0][1]
    for eff, r in RATE_PATH:
        if d >= eff:
            rate = r
    return rate


def build_statement_history() -> list[dict]:
    """Build Inst.1..33 from statement EMI cash + phased disbursals + rate path.

    Anchors EMI#33 closing_balance to live OS so principal/interest totals match
    the statement finance summary (prin ₹10,76,907 / int ₹19,03,699).
    """
    emis: list[tuple[int, date, Decimal]] = []
    for start, end, amt, first in EMI_BLOCKS:
        for n in range(start, end + 1):
            emis.append((n, _add_months(first, n - start), amt))

    bal = Decimal("0.00")
    applied = 0

    def apply_disb_before(cutoff: date) -> None:
        nonlocal bal, applied
        while applied < len(DISBURSALS) and DISBURSALS[applied][0] < cutoff:
            bal += DISBURSALS[applied][1]
            applied += 1

    apply_disb_before(emis[0][1])
    rows: list[dict] = []
    for n, due, emi in emis:
        apply_disb_before(due)
        rate = _rate_on(due)
        opening = bal
        interest = (opening * rate / Decimal("1200")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        principal = emi - interest
        if principal < 0:
            principal = Decimal("0.00")
            interest = emi
        closing = opening - principal
        bal = closing
        phase = "full_emi" if due >= FIRST_FULL_EMI_DATE else "partial_emi"
        rows.append(
            {
                "emi_number": n,
                "due_date": due,
                "emi_amount": emi,
                "rate": rate,
                "opening_balance": opening,
                "interest_component": interest,
                "principal_component": principal,
                "closing_balance": closing,
                "phase": phase,
            }
        )

    # OS anchor on last paid row — absorbs day-count/rate-path residuals
    last = rows[-1]
    delta = last["closing_balance"] - OS_PRINCIPAL
    last["principal_component"] = (last["principal_component"] + delta).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    last["interest_component"] = (last["emi_amount"] - last["principal_component"]).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    last["closing_balance"] = OS_PRINCIPAL
    last["os_anchored"] = True
    return rows


async def main() -> dict:
    assert len(DISPLAY_NAME) <= 255, f"display_name too long: {len(DISPLAY_NAME)}"
    history = build_statement_history()
    assert len(history) == PAID_COUNT
    assert history[-1]["closing_balance"] == OS_PRINCIPAL
    assert history[28]["due_date"] == FIRST_FULL_EMI_DATE  # Inst.29
    assert history[28]["emi_amount"] == EMI_AMOUNT

    async with async_session_maker() as session:
        loan = await session.get(Account, LOAN_ID)
        pru = await session.get(Account, PRU_ID)
        savings = await session.get(Account, SAVINGS_ID)
        if not loan or loan.type != "loan":
            raise SystemExit(f"Loan {LOAN_ID} not found")
        if not pru or pru.type != "loan":
            raise SystemExit("Pru loan missing — abort to avoid collateral damage")
        if not savings:
            raise SystemExit(f"Savings {SAVINGS_ID} not found")

        pru_name_before = pru.name
        pru_bal_before = pru.balance

        # --- 1) Account enrichment + KM chips ---
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
        loan.loan_kind = "home"
        if not savings.masked_number:
            savings.masked_number = "8757"
        if not savings.external_id:
            savings.external_id = "003901608757"
        await session.commit()
        await session.refresh(loan)

        # --- 2) Wipe current-version schedule; write statement-faithful paid rows ---
        old_version = loan.current_schedule_version or 1
        new_version = old_version + 1
        loan.current_schedule_version = new_version

        # Soft-retain old versions; only need current to be correct
        km_blob = json.dumps(KM_ASSUMPTIONS, separators=(",", ":"))
        paid_entries: list[LoanAmortizationSchedule] = []
        for row in history:
            notes = (
                f"stmt {row['phase']} @ {row['rate']}% | "
                f"KM chips: disbursal_phases=5;pre_emi/partial→full@May-26;"
                f"rate_path=9→8.5→8→7.75;proj=cash_hist→current_EMI"
            )
            if row["emi_number"] == 1:
                notes = (
                    f"Pre-EMI {PRE_EMI[0].isoformat()} ₹{PRE_EMI[1]} (broken period, "
                    f"not in 33). {notes}. KM_JSON={km_blob}"
                )[:1000]
            if row.get("os_anchored"):
                notes = (
                    f"Paid through EMI#{PAID_COUNT} as-of {AS_OF.isoformat()}. "
                    f"OS anchor ₹{OS_PRINCIPAL}. First full EMI {FIRST_FULL_EMI_DATE}. "
                    f"5 disbursals. DO_NOT_FLATTEN. {notes}"
                )[:1000]
            entry = LoanAmortizationSchedule(
                id=uuid.uuid4(),
                account_id=LOAN_ID,
                workspace_id=loan.workspace_id,
                schedule_version=new_version,
                emi_number=row["emi_number"],
                due_date=row["due_date"],
                principal_component=row["principal_component"],
                interest_component=row["interest_component"],
                emi_amount=row["emi_amount"],
                opening_balance=row["opening_balance"],
                closing_balance=row["closing_balance"],
                payment_status="paid",
                actual_payment_date=row["due_date"],
                actual_amount_paid=row["emi_amount"],
                notes=notes[:1000],
            )
            session.add(entry)
            paid_entries.append(entry)
        await session.commit()

        # --- 3) Future 130 from live OS @ 7.75% / EMI ₹1,21,543 ---
        new_entries = await loan_schedule_service.regenerate_schedule(
            session,
            LOAN_ID,
            from_emi_number=PAID_COUNT + 1,
            new_params={
                "new_principal_balance": OS_PRINCIPAL,
                "new_interest_rate": RATE,
                "new_tenure_months": PENDING_COUNT,
                "new_emi_amount": EMI_AMOUNT,
            },
        )
        if new_entries:
            new_entries[0].notes = (
                f"NRP future from OS ₹{OS_PRINCIPAL} @ {RATE}% EMI ₹{EMI_AMOUNT}. "
                f"History=statement cash (NOT flattened). "
                f"KM:disbursal_phases=5;pre_emi/partial→full@May-26;"
                f"rate_path=9→8.5→8→7.75. Accrued≈₹{ACCRUED_INTEREST}@{AS_OF}."
            )[:1000]
            await session.commit()

        await session.refresh(loan)
        loan.balance = OS_PRINCIPAL
        loan.emi_amount = EMI_AMOUNT
        loan.interest_rate = RATE
        loan.display_name = DISPLAY_NAME
        await session.commit()

        # --- 4) Recurring EMI on savings — current full EMI only (no past rows) ---
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
            # Start of full-EMI era for next occurrence; do not invent past recurrings
            if not rec.start_date or rec.start_date < FIRST_FULL_EMI_DATE:
                rec.start_date = FIRST_FULL_EMI_DATE
            if rec.next_occurrence is None or rec.next_occurrence <= AS_OF:
                rec.next_occurrence = date(2026, 10, 5)
            await session.commit()
            await session.refresh(rec)
        else:
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

        # --- 5) Verify ---
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
        paid_emi_sum = sum((e.emi_amount for e in paid), Decimal("0"))
        paid_prin = sum((e.principal_component for e in paid), Decimal("0"))
        paid_int = sum((e.interest_component for e in paid), Decimal("0"))

        first_full = next(
            (e for e in paid if e.emi_amount == EMI_AMOUNT), None
        )
        early_amis = sorted({str(e.emi_amount) for e in paid if e.emi_number <= 28})

        if pru.name != pru_name_before or pru.balance != pru_bal_before:
            raise SystemExit("Pru loan mutated — abort")
        if len(paid) != PAID_COUNT or len(pending) != PENDING_COUNT:
            raise SystemExit(
                f"Count mismatch paid={len(paid)} pending={len(pending)}"
            )
        if paid_emi_sum != Decimal("2980606.00"):
            raise SystemExit(f"Paid EMI sum {paid_emi_sum} != statement 2980606")
        if paid[0].emi_amount == EMI_AMOUNT:
            raise SystemExit("Flatten detected: EMI#1 still full EMI")

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
            "paid": len(paid),
            "pending": len(pending),
            "paid_emi_sum": str(paid_emi_sum),
            "paid_principal_sum": str(paid_prin),
            "paid_interest_sum": str(paid_int),
            "early_emi_amounts": early_amis,
            "first_full_emi_date": first_full.due_date.isoformat() if first_full else None,
            "first_full_emi_number": first_full.emi_number if first_full else None,
            "disbursal_count": len(DISBURSALS),
            "pre_emi": {"date": PRE_EMI[0].isoformat(), "amount": str(PRE_EMI[1])},
            "km_assumptions": KM_ASSUMPTIONS,
            "regenerated_future": len(new_entries),
            "future_instalments_sum": str(future_emi_sum),
            "accrued_interest_note": str(ACCRUED_INTEREST),
            "recurring_id": str(rec.id),
            "recurring_description": rec.description,
            "recurring_amount": str(rec.amount),
            "recurring_start": rec.start_date.isoformat() if rec.start_date else None,
            "recurring_next": rec.next_occurrence.isoformat() if rec.next_occurrence else None,
            "recurring_created": created_rec,
            "savings_id": str(SAVINGS_ID),
            "savings_external_id": savings.external_id,
            "pru_untouched": True,
            "money_loan_url": f"https://money.planetfinance.cloud/loans/{LOAN_ID}",
            "as_of": AS_OF.isoformat(),
            "seeded_at": datetime.now(timezone.utc).isoformat(),
            "change_vs_old": {
                "old": "flattened full EMI ₹121543 from sanction; 33 paid as full EMI",
                "new": (
                    f"5 disbursals; Pre-EMI+partial→full; first full EMI "
                    f"{FIRST_FULL_EMI_DATE}; paid EMI sum ₹29,80,606; "
                    f"paid/pending still 33/130; OS ₹{OS_PRINCIPAL}"
                ),
            },
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
    # Local unit check of history builder without DB
    if len(sys.argv) > 1 and sys.argv[1] == "--check-history":
        rows = build_statement_history()
        print(
            json.dumps(
                {
                    "count": len(rows),
                    "emi1": {
                        "date": rows[0]["due_date"].isoformat(),
                        "emi": str(rows[0]["emi_amount"]),
                    },
                    "emi29_full": {
                        "date": rows[28]["due_date"].isoformat(),
                        "emi": str(rows[28]["emi_amount"]),
                    },
                    "emi33_close": str(rows[-1]["closing_balance"]),
                    "paid_emi_sum": str(sum(r["emi_amount"] for r in rows)),
                    "paid_prin": str(sum(r["principal_component"] for r in rows)),
                    "paid_int": str(sum(r["interest_component"] for r in rows)),
                    "display_name_len": len(DISPLAY_NAME),
                },
                indent=2,
            )
        )
        sys.exit(0)
    asyncio.run(main())
