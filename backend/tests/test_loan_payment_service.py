from datetime import date, timedelta
from decimal import Decimal
import pytest
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.loan_payment_service import (
    auto_link_transactions,
    link_transaction_to_entry,
    mark_payment_status,
    simulate_prepayment,
    record_prepayment,
)
from app.services.loan_schedule_service import generate_amortization_schedule
from app.models.account import Account
from app.models.transaction import Transaction


@pytest.mark.asyncio
async def test_auto_link_transactions_exact_match(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
):
    """Test auto-linking with exact date and amount match."""
    # Create loan account with schedule
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Test Loan",
        type="loan",
        balance=Decimal("100000.00"),
        currency="USD",
        original_principal=Decimal("100000.00"),
        interest_rate=Decimal("10.00"),
        tenure_months=12,
        emi_amount=Decimal("8791.59"),
        disbursed_on=date(2026, 8, 1),
        emi_day=5,
        current_schedule_version=1,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)

    entries = await generate_amortization_schedule(session, account.id)

    # Create transaction matching first EMI
    transaction = Transaction(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        account_id=account.id,
        description="EMI Payment",
        amount=Decimal("8791.59"),
        currency="USD",
        date=entries[0].due_date,
        effective_date=entries[0].due_date,
        type="debit",
        source="manual",
    )
    session.add(transaction)
    await session.commit()

    # Auto-link
    matches, auto_linked, review_needed = await auto_link_transactions(
        session, account.id, date_tolerance_days=5, amount_tolerance_pct=Decimal("2.0")
    )

    assert auto_linked == 1
    assert review_needed == 0
    assert len(matches) == 1
    assert matches[0]["confidence"] == "exact"


@pytest.mark.asyncio
async def test_simulate_prepayment_reduce_emi(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
):
    """Test prepayment simulation for reduce EMI option."""
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Test Loan",
        type="loan",
        balance=Decimal("500000.00"),
        currency="USD",
        original_principal=Decimal("500000.00"),
        interest_rate=Decimal("8.50"),
        tenure_months=60,
        emi_amount=Decimal("10289.52"),
        disbursed_on=date(2026, 1, 1),
        emi_day=5,
        current_schedule_version=1,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)

    await generate_amortization_schedule(session, account.id)

    # Simulate prepayment of 100k after 12 months
    simulation = await simulate_prepayment(
        session, account.id, prepayment_amount=Decimal("100000.00"), prepayment_date=date(2027, 1, 5)
    )

    # Verify reduce_emi option
    assert simulation["reduce_emi_option"]["new_emi_amount"] < Decimal("10289.52")
    assert simulation["reduce_emi_option"]["tenure_months"] == 48  # remaining
    assert simulation["reduce_emi_option"]["total_interest_saved"] > Decimal("0")

    # Verify reduce_tenure option
    assert simulation["reduce_tenure_option"]["emi_amount"] == Decimal("10289.52")
    assert simulation["reduce_tenure_option"]["months_saved"] > 0


@pytest.mark.asyncio
async def test_record_prepayment_reduce_tenure(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
):
    """Test recording a prepayment with reduce tenure method."""
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Test Loan",
        type="loan",
        balance=Decimal("100000.00"),
        currency="USD",
        original_principal=Decimal("100000.00"),
        interest_rate=Decimal("10.00"),
        tenure_months=12,
        emi_amount=Decimal("8791.59"),
        disbursed_on=date(2026, 8, 1),
        emi_day=5,
        current_schedule_version=1,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)

    await generate_amortization_schedule(session, account.id)

    # Record prepayment
    prepayment = await record_prepayment(
        session,
        account.id,
        prepayment_amount=Decimal("20000.00"),
        prepayment_date=date(2026, 10, 5),
        method="reduce_tenure",
        transaction_id=None,
    )

    assert prepayment.recalculation_method == "reduce_tenure"
    assert prepayment.schedule_version_before == 1
    assert prepayment.schedule_version_after == 2
    assert prepayment.months_saved is not None

    # Verify account updated
    await session.refresh(account)
    assert account.current_schedule_version == 2
    assert account.total_prepayments == Decimal("20000.00")
