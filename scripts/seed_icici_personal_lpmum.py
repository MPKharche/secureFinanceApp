#!/usr/bin/env python3
"""Seed ICICI Bank Personal Loan - Example/Demo Data.

Idempotent data seed — does NOT create duplicate loans.

This is a SAMPLE/DEMO seed script showing how to:
  - Create loan accounts with amortization schedules
  - Link to existing users (configurable)
  - Set up recurring transaction reminders
  - Generate accurate EMI calculations

USAGE:
  1. Update USER_EMAIL to match your demo/test user
  2. Adjust loan parameters as needed
  3. Run: python3 scripts/seed_icici_personal_lpmum.py

NOTE: This creates DEMO DATA only. Replace with actual loan details
      from your own statements. Never commit real user data to Git.

Loan details (example values):
  - Principal: ₹10,00,000
  - Rate: 10.7% fixed (monthly reducing balance)
  - Tenure: 60 months
  - EMI: ₹21,703
  - Start Date: 05-Aug-2026
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
from app.models.user import User
from app.models.workspace import Workspace
from app.models.category import Category
from app.models.loan_schedule import LoanAmortizationSchedule
from app.models.recurring_transaction import RecurringTransaction
from app.schemas.recurring_transaction import RecurringTransactionCreate
from app.services import loan_schedule_service, recurring_transaction_service

# ============================================================================
# CONFIGURATION - Update these for your use case
# ============================================================================

# User to attach loan to (use demo user or your own)
USER_EMAIL = "demo@example.com"  # Change to your test user email

# Loan parameters (example values - replace with your actual loan)
LOAN_ACCOUNT_NO = "LPMUM00052503715"  # Example account number
PRINCIPAL = Decimal("1000000.00")
RATE = Decimal("10.70")
TENURE_MONTHS = 60
EMI_AMOUNT = Decimal("21703.00")
START_DATE = date(2026, 8, 5)
EMI_DAY = 5
CURRENCY = "INR"
LOAN_KIND = "personal"

# ============================================================================

# Display name with key info
DISPLAY_NAME = (
    f"ICICI Personal · {RATE}% · EMI ₹{EMI_AMOUNT:,} · {TENURE_MONTHS}m | "
    f"{LOAN_ACCOUNT_NO[-4:]} | ₹{PRINCIPAL/100000:.0f}L@{START_DATE.strftime('%b-%y')}"
)

# Expected totals for validation (adjust based on your loan)
EXPECTED_TOTAL_PAYMENT = Decimal("1302036.00")  # Principal + Interest
EXPECTED_TOTAL_INTEREST = Decimal("302036.00")

OUT = Path(__file__).resolve().parent / "seed_loan_result.json"


def _add_months(d: date, m: int) -> date:
    """Add months to date, handling month-end edge cases."""
    y = d.year + (d.month - 1 + m) // 12
    mo = (d.month - 1 + m) % 12 + 1
    day = min(d.day, calendar.monthrange(y, mo)[1])
    return date(y, mo, day)


async def find_or_create_user(session) -> tuple[User, Workspace]:
    """Find existing user or create demo user."""
    # Try to find user by configured email
    result = await session.execute(
        select(User).where(User.email == USER_EMAIL)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise SystemExit(
            f"User '{USER_EMAIL}' not found. Please:\n"
            f"  1. Create a user first, or\n"
            f"  2. Update USER_EMAIL in this script to match an existing user"
        )
    
    # Get user's workspace
    result = await session.execute(
        select(Workspace).where(Workspace.id == user.workspace_id)
    )
    workspace = result.scalar_one()
    
    return user, workspace


async def find_or_create_savings_account(
    session, user: User, workspace: Workspace
) -> Account:
    """Find existing savings account or create one."""
    # Look for existing ICICI savings
    result = await session.execute(
        select(Account).where(
            Account.user_id == user.id,
            Account.type == "checking",
            Account.currency == CURRENCY,
        )
    )
    accounts = list(result.scalars().all())
    
    if accounts:
        return accounts[0]
    
    # Create new savings account
    savings = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=workspace.id,
        name="ICICI Savings",
        display_name="ICICI Bank Savings Account",
        external_id="003901608757",
        masked_number="8757",
        type="checking",
        balance=Decimal("500000.00"),  # Starting balance
        currency=CURRENCY,
    )
    session.add(savings)
    await session.flush()
    return savings


async def find_or_create_emi_category(
    session, user: User, workspace: Workspace
) -> Category:
    """Find or create EMI/Loan Payment category."""
    result = await session.execute(
        select(Category).where(
            Category.workspace_id == workspace.id,
            Category.name.ilike("%loan%"),
        )
    )
    category = result.scalar_one_or_none()
    
    if category:
        return category
    
    # Create new category
    category = Category(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=workspace.id,
        name="Loan EMI",
        type="debit",
        color="#e74c3c",
        icon="💳",
    )
    session.add(category)
    await session.flush()
    return category


def build_amortization_schedule() -> list[dict]:
    """Build 60-month amortization schedule using reducing balance method.
    
    Returns list of dicts with keys:
        emi_number, due_date, emi_amount, opening_balance,
        interest_component, principal_component, closing_balance
    """
    monthly_rate = RATE / Decimal("1200")  # 10.7% / 12 / 100
    balance = PRINCIPAL
    rows = []
    
    for i in range(1, TENURE_MONTHS + 1):
        due_date = _add_months(START_DATE, i - 1)
        
        opening = balance
        interest = (opening * monthly_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        principal = EMI_AMOUNT - interest
        
        # Last EMI: adjust for rounding residuals
        if i == TENURE_MONTHS:
            principal = opening
            emi = principal + interest
        else:
            emi = EMI_AMOUNT
        
        closing = opening - principal
        balance = closing
        
        rows.append({
            "emi_number": i,
            "due_date": due_date,
            "emi_amount": emi,
            "opening_balance": opening,
            "interest_component": interest,
            "principal_component": principal,
            "closing_balance": closing,
        })
    
    return rows


async def main() -> dict:
    """Main seed function."""
    print(f"Seeding ICICI Personal Loan {LOAN_ACCOUNT_NO}...")
    
    # Validate display name length
    assert len(DISPLAY_NAME) <= 255, f"display_name too long: {len(DISPLAY_NAME)}"
    
    # Build and validate schedule
    schedule_data = build_amortization_schedule()
    assert len(schedule_data) == TENURE_MONTHS
    assert schedule_data[-1]["closing_balance"] == Decimal("0.00")
    
    total_emi = sum(row["emi_amount"] for row in schedule_data)
    total_interest = sum(row["interest_component"] for row in schedule_data)
    total_principal = sum(row["principal_component"] for row in schedule_data)
    
    print(f"  Schedule validation:")
    print(f"    Total payment: ₹{total_emi:,.2f} (expected ₹{EXPECTED_TOTAL_PAYMENT:,.2f})")
    print(f"    Total interest: ₹{total_interest:,.2f} (expected ₹{EXPECTED_TOTAL_INTEREST:,.2f})")
    print(f"    Total principal: ₹{total_principal:,.2f} (expected ₹{PRINCIPAL:,.2f})")
    
    async with async_session_maker() as session:
        # 1. Find or create user and workspace
        user, workspace = await find_or_create_user(session)
        print(f"  Using user: {user.email} (workspace: {workspace.name})")
        
        # 2. Check if loan already exists
        result = await session.execute(
            select(Account).where(
                Account.user_id == user.id,
                Account.external_id == LOAN_ACCOUNT_NO,
            )
        )
        existing_loan = result.scalar_one_or_none()
        
        if existing_loan:
            print(f"  ⚠️  Loan {LOAN_ACCOUNT_NO} already exists (ID: {existing_loan.id})")
            print(f"     Skipping creation. Run with --force to recreate.")
            return {
                "status": "exists",
                "loan_id": str(existing_loan.id),
                "message": "Loan already exists"
            }
        
        # 3. Find or create savings account
        savings = await find_or_create_savings_account(session, user, workspace)
        print(f"  Savings account: {savings.name} (ID: {savings.id})")
        
        # 4. Find or create EMI category
        emi_category = await find_or_create_emi_category(session, user, workspace)
        print(f"  EMI category: {emi_category.name} (ID: {emi_category.id})")
        
        # 5. Create loan account
        loan = Account(
            id=uuid.uuid4(),
            user_id=user.id,
            workspace_id=workspace.id,
            name=f"ICICI Personal Loan {LOAN_ACCOUNT_NO[-4:]}",
            display_name=DISPLAY_NAME,
            external_id=LOAN_ACCOUNT_NO,
            masked_number=LOAN_ACCOUNT_NO[-4:],
            type="loan",
            loan_kind=LOAN_KIND,
            balance=PRINCIPAL,  # Outstanding principal
            currency=CURRENCY,
            original_principal=PRINCIPAL,
            interest_rate=RATE,
            tenure_months=TENURE_MONTHS,
            emi_amount=EMI_AMOUNT,
            disbursed_on=START_DATE,
            emi_day=EMI_DAY,
            current_schedule_version=1,
        )
        session.add(loan)
        await session.flush()
        print(f"  ✓ Loan account created: {loan.id}")
        
        # 6. Create amortization schedule
        for row in schedule_data:
            entry = LoanAmortizationSchedule(
                id=uuid.uuid4(),
                account_id=loan.id,
                workspace_id=workspace.id,
                schedule_version=1,
                emi_number=row["emi_number"],
                due_date=row["due_date"],
                principal_component=row["principal_component"],
                interest_component=row["interest_component"],
                emi_amount=row["emi_amount"],
                opening_balance=row["opening_balance"],
                closing_balance=row["closing_balance"],
                payment_status="scheduled",
                notes=f"EMI #{row['emi_number']} of {TENURE_MONTHS}" if row["emi_number"] == 1 
                      else None,
            )
            session.add(entry)
        
        await session.commit()
        print(f"  ✓ Amortization schedule created: {TENURE_MONTHS} entries")
        
        # 7. Create recurring transaction for EMI reminders
        rec_desc = f"ICICI Personal Loan EMI - {LOAN_ACCOUNT_NO}"
        rec = await recurring_transaction_service.create_recurring_transaction(
            session,
            workspace.id,
            user.id,
            RecurringTransactionCreate(
                description=rec_desc,
                amount=EMI_AMOUNT,
                currency=CURRENCY,
                type="debit",
                frequency="monthly",
                day_of_month=EMI_DAY,
                start_date=_add_months(START_DATE, 1),  # Next month
                account_id=savings.id,
                category_id=emi_category.id,
                auto_generate=False,  # Manual linking preferred
            ),
        )
        print(f"  ✓ Recurring transaction created: {rec.id}")
        
        # 8. Verify schedule
        result = await session.execute(
            select(LoanAmortizationSchedule)
            .where(
                LoanAmortizationSchedule.account_id == loan.id,
                LoanAmortizationSchedule.schedule_version == 1,
            )
            .order_by(LoanAmortizationSchedule.emi_number)
        )
        entries = list(result.scalars().all())
        
        assert len(entries) == TENURE_MONTHS
        assert entries[0].opening_balance == PRINCIPAL
        assert entries[-1].closing_balance == Decimal("0.00")
        
        # Calculate totals
        sched_total_emi = sum(e.emi_amount for e in entries)
        sched_total_interest = sum(e.interest_component for e in entries)
        sched_total_principal = sum(e.principal_component for e in entries)
        
        result_payload = {
            "status": "created",
            "loan_id": str(loan.id),
            "external_id": LOAN_ACCOUNT_NO,
            "borrower": BORROWER_NAME,
            "loan_account": {
                "name": loan.name,
                "display_name": loan.display_name,
                "type": loan.type,
                "loan_kind": loan.loan_kind,
                "balance": str(loan.balance),
                "currency": loan.currency,
            },
            "loan_parameters": {
                "principal": str(PRINCIPAL),
                "interest_rate": str(RATE),
                "tenure_months": TENURE_MONTHS,
                "emi_amount": str(EMI_AMOUNT),
                "disbursed_on": START_DATE.isoformat(),
                "emi_day": EMI_DAY,
            },
            "schedule": {
                "version": 1,
                "total_entries": len(entries),
                "first_emi_date": entries[0].due_date.isoformat(),
                "last_emi_date": entries[-1].due_date.isoformat(),
                "total_payment": str(sched_total_emi),
                "total_interest": str(sched_total_interest),
                "total_principal": str(sched_total_principal),
            },
            "validation": {
                "expected_total_payment": str(EXPECTED_TOTAL_PAYMENT),
                "expected_total_interest": str(EXPECTED_TOTAL_INTEREST),
                "total_payment_match": sched_total_emi == EXPECTED_TOTAL_PAYMENT,
                "closing_balance_zero": entries[-1].closing_balance == Decimal("0.00"),
            },
            "recurring_transaction": {
                "id": str(rec.id),
                "description": rec.description,
                "amount": str(rec.amount),
                "frequency": rec.frequency,
                "day_of_month": rec.day_of_month,
                "start_date": rec.start_date.isoformat() if rec.start_date else None,
                "next_occurrence": rec.next_occurrence.isoformat() if rec.next_occurrence else None,
            },
            "savings_account_id": str(savings.id),
            "emi_category_id": str(emi_category.id),
            "ui_urls": {
                "loan_detail": f"http://localhost:3000/loans/{loan.id}",
                "schedule": f"http://localhost:3000/loans/{loan.id}/schedule",
            },
            "seeded_at": datetime.now(timezone.utc).isoformat(),
        }
        
        OUT.write_text(json.dumps(result_payload, indent=2))
        print(f"\n✓ Seed complete!")
        print(f"  Loan ID: {loan.id}")
        print(f"  Schedule: {len(entries)} entries")
        print(f"  Total payment: ₹{sched_total_emi:,.2f}")
        print(f"  Output: {OUT}")
        
        return result_payload


if __name__ == "__main__":
    asyncio.run(main())
