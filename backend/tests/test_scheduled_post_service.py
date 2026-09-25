"""Tests for G0 guided post-on-due (dual-ledger)."""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.asset import Asset
from app.models.recurring_transaction import RecurringTransaction
from app.schemas.recurring_transaction import RecurringTransactionCreate
from app.services import recurring_transaction_service
from app.services.loan_schedule_service import generate_interest_only_schedule
from app.services.scheduled_post_service import ScheduledPostError, post_recurring_occurrence


@pytest.mark.asyncio
async def test_post_premium_creates_debit_and_advances(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
):
    cash = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Savings",
        type="savings",
        balance=Decimal("100000"),
        currency="INR",
    )
    session.add(cash)
    await session.commit()

    rec, _ = await recurring_transaction_service.create_recurring_transaction(
        session,
        workspace_id,
        user_id,
        RecurringTransactionCreate(
            description="Pru Premium",
            amount=Decimal("10000"),
            currency="INR",
            type="debit",
            frequency="monthly",
            start_date=date.today() - timedelta(days=30),
            account_id=cash.id,
            auto_generate=False,
        ),
    )
    rec.next_occurrence = date.today() - timedelta(days=1)
    await session.commit()

    result = await post_recurring_occurrence(
        session, workspace_id, user_id, rec.id,
    )
    assert result["already_posted"] is False
    assert len(result["transaction_ids"]) == 1
    await session.refresh(rec)
    assert rec.next_occurrence > date.today() - timedelta(days=1)


@pytest.mark.asyncio
async def test_post_interest_transfer_links_schedule(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
):
    cash = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Savings",
        type="savings",
        balance=Decimal("100000"),
        currency="INR",
    )
    loan = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Policy Loan",
        type="loan",
        balance=Decimal("174805"),
        currency="INR",
        original_principal=Decimal("160000"),
        interest_rate=Decimal("7.96"),
        tenure_months=24,
        disbursed_on=date(2025, 3, 25),
        emi_day=25,
        current_schedule_version=1,
    )
    session.add_all([cash, loan])
    await session.commit()

    entries = await generate_interest_only_schedule(session, loan.id, cadence_months=6)
    first_due = entries[0].due_date

    rec, _ = await recurring_transaction_service.create_recurring_transaction(
        session,
        workspace_id,
        user_id,
        RecurringTransactionCreate(
            description="Pru Interest",
            amount=entries[0].emi_amount,
            currency="INR",
            type="debit",
            frequency="semiannual",
            start_date=first_due,
            account_id=cash.id,
            auto_generate=False,
        ),
    )
    rec.next_occurrence = first_due
    await session.commit()

    asset = Asset(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Pru Policy",
        type="insurance",
        currency="INR",
        external_metadata={
            "g0_assumptions": {
                "loan_account_id": str(loan.id),
                "cash_account_id": str(cash.id),
                "linked_interest_recurring_id": str(rec.id),
                "interest_amount_half_yearly": float(entries[0].emi_amount),
                "loan_rate_percent": 7.96,
            }
        },
    )
    session.add(asset)
    await session.commit()

    # Post as if due today when schedule row is in the past or today
    pay_date = min(date.today(), first_due) if first_due <= date.today() else first_due
    if pay_date > date.today():
        pytest.skip("Schedule due date still in future in this test run")

    rec.next_occurrence = pay_date
    await session.commit()

    result = await post_recurring_occurrence(
        session, workspace_id, user_id, rec.id, payment_date=pay_date,
    )
    assert result["already_posted"] is False
    assert result["credit_leg_id"] is not None
    assert result["schedule_entry_id"] is not None
    assert result["post_kind"] == "interest_half_yearly"


@pytest.mark.asyncio
async def test_post_rejects_far_future(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
):
    cash = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Savings",
        type="savings",
        balance=Decimal("1000"),
        currency="INR",
    )
    session.add(cash)
    await session.commit()

    rec, _ = await recurring_transaction_service.create_recurring_transaction(
        session,
        workspace_id,
        user_id,
        RecurringTransactionCreate(
            description="Future bill",
            amount=Decimal("100"),
            currency="INR",
            type="debit",
            frequency="monthly",
            start_date=date.today() + timedelta(days=60),
            account_id=cash.id,
            auto_generate=False,
        ),
    )
    with pytest.raises(ScheduledPostError, match="not due yet"):
        await post_recurring_occurrence(session, workspace_id, user_id, rec.id)
