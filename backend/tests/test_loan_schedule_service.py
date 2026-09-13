from datetime import date, timedelta
from decimal import Decimal
import pytest
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.loan_schedule_service import (
    calculate_emi,
    generate_amortization_schedule,
    get_schedule,
    update_schedule_entry,
    bulk_update_dates,
    regenerate_schedule,
)
from app.models.account import Account


def test_calculate_emi_standard():
    """Test EMI calculation with known values."""
    # Loan: 1,000,000 principal, 12% annual rate (1% monthly), 12 months
    # Expected EMI ≈ 88,848.79
    principal = Decimal("1000000.00")
    annual_rate = Decimal("12.00")
    tenure_months = 12

    emi = calculate_emi(principal, annual_rate, tenure_months)

    assert emi == Decimal("88848.79")


def test_calculate_emi_longer_tenure():
    """Test EMI calculation for longer tenure."""
    # Loan: 500,000 principal, 8.5% annual rate, 60 months
    # Expected EMI ≈ 10,289.52
    principal = Decimal("500000.00")
    annual_rate = Decimal("8.50")
    tenure_months = 60

    emi = calculate_emi(principal, annual_rate, tenure_months)

    assert emi == Decimal("10289.52")


def test_calculate_emi_zero_interest():
    """Test EMI with zero interest rate."""
    principal = Decimal("120000.00")
    annual_rate = Decimal("0.00")
    tenure_months = 12

    emi = calculate_emi(principal, annual_rate, tenure_months)

    # With 0% interest, EMI = principal / tenure
    assert emi == Decimal("10000.00")


@pytest.mark.asyncio
async def test_generate_amortization_schedule(session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID):
    """Test schedule generation for a loan account."""
    # Create loan account
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Home Loan",
        type="loan",
        balance=Decimal("1000000.00"),
        currency="USD",
        original_principal=Decimal("1000000.00"),
        interest_rate=Decimal("12.00"),
        tenure_months=12,
        emi_amount=Decimal("88848.79"),
        disbursed_on=date(2026, 8, 1),
        emi_day=5,
        current_schedule_version=1,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)

    # Generate schedule
    entries = await generate_amortization_schedule(session, account.id, version=1)

    # Verify schedule
    assert len(entries) == 12
    assert entries[0].emi_number == 1
    assert entries[0].due_date == date(2026, 9, 5)
    assert entries[0].opening_balance == Decimal("1000000.00")
    assert entries[0].payment_status == "scheduled"

    # First EMI breakdown
    assert entries[0].interest_component == Decimal("10000.00")  # 1% of 1M
    assert entries[0].principal_component == Decimal("78848.79")  # EMI - interest
    assert entries[0].closing_balance == Decimal("921151.21")  # 1M - principal

    # Last EMI should close loan
    assert entries[11].emi_number == 12
    assert entries[11].closing_balance < Decimal("1.00")  # near zero (rounding)


@pytest.mark.asyncio
async def test_generate_schedule_zero_interest(session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID):
    """Test schedule generation with zero interest."""
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Interest-free Loan",
        type="loan",
        balance=Decimal("120000.00"),
        currency="USD",
        original_principal=Decimal("120000.00"),
        interest_rate=Decimal("0.00"),
        tenure_months=12,
        emi_amount=Decimal("10000.00"),
        disbursed_on=date(2026, 8, 1),
        emi_day=10,
        current_schedule_version=1,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)

    entries = await generate_amortization_schedule(session, account.id, version=1)

    assert len(entries) == 12
    # All EMIs should be pure principal
    for entry in entries:
        assert entry.interest_component == Decimal("0.00")
        assert entry.principal_component == Decimal("10000.00")


@pytest.mark.asyncio
async def test_update_schedule_entry(session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID):
    """Test updating a single schedule entry."""
    # Create loan and generate schedule
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
    entry_to_update = entries[0]

    # Update due date and notes
    updates = {"due_date": date(2026, 9, 10), "notes": "Payment rescheduled"}
    updated_entry, affected_count = await update_schedule_entry(session, entry_to_update.id, updates)

    assert updated_entry.due_date == date(2026, 9, 10)
    assert updated_entry.notes == "Payment rescheduled"
    assert affected_count == 0  # Date change doesn't trigger recalculation


@pytest.mark.asyncio
async def test_bulk_update_dates_shift(session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID):
    """Test bulk shifting of schedule dates."""
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
    original_first_due = entries[0].due_date

    # Shift all dates by +10 days
    updated_count = await bulk_update_dates(session, account.id, shift_days=10, new_emi_day=None, from_emi_number=1)

    assert updated_count == 12

    # Verify shift
    updated_entries = await get_schedule(session, account.id)
    assert updated_entries[0].due_date == original_first_due + timedelta(days=10)


@pytest.mark.asyncio
async def test_regenerate_schedule_from_midpoint(session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID):
    """Test regenerating schedule from a specific EMI number."""
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

    # Regenerate from EMI 7 with new balance (simulating partial prepayment)
    new_params = {
        "new_principal_balance": Decimal("50000.00"),
        "new_interest_rate": Decimal("10.00"),
        "new_tenure_months": 6,
    }
    new_entries = await regenerate_schedule(session, account.id, from_emi_number=7, new_params=new_params)

    # Should have 6 new entries (EMI 7-12)
    assert len(new_entries) == 6
    assert new_entries[0].emi_number == 7
    assert new_entries[0].schedule_version == 2
    assert new_entries[0].opening_balance == Decimal("50000.00")

    # Account version should be incremented
    await session.refresh(account)
    assert account.current_schedule_version == 2


@pytest.mark.asyncio
async def test_interest_only_emi_does_not_emit_negative_interest(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
):
    """When EMI ≈ monthly interest, last EMI must balloon — never negative interest."""
    principal = Decimal("160000.00")
    rate = Decimal("7.96")
    # EMI equal to monthly interest → non-amortizing until balloon
    monthly_interest = (principal * rate / Decimal("1200")).quantize(Decimal("0.01"))
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Policy Loan Interest-Only Style",
        type="loan",
        balance=Decimal("174805.00"),
        currency="INR",
        original_principal=principal,
        interest_rate=rate,
        tenure_months=12,
        emi_amount=monthly_interest,
        disbursed_on=date(2025, 3, 25),
        emi_day=25,
        current_schedule_version=1,
    )
    session.add(account)
    await session.commit()

    entries = await generate_amortization_schedule(session, account.id, version=1)
    assert len(entries) == 12
    assert all(e.interest_component >= 0 for e in entries)
    assert entries[-1].principal_component == principal
    assert entries[-1].closing_balance == Decimal("0.00")
    assert entries[-1].emi_amount == entries[-1].principal_component + entries[-1].interest_component


@pytest.mark.asyncio
async def test_generate_interest_only_half_yearly(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
):
    from app.services.loan_schedule_service import generate_interest_only_schedule

    principal = Decimal("160000.00")
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="ICICI Pru Policy Loan",
        type="loan",
        balance=Decimal("174805.00"),
        currency="INR",
        original_principal=principal,
        interest_rate=Decimal("7.96"),
        tenure_months=24,
        emi_amount=None,
        disbursed_on=date(2025, 3, 25),
        emi_day=25,
        current_schedule_version=1,
    )
    session.add(account)
    await session.commit()

    entries = await generate_interest_only_schedule(
        session, account.id, cadence_months=6, include_principal_balloon=True
    )
    # 24/6 = 4 interest periods + 1 balloon
    assert len(entries) == 5
    half_year_interest = (principal * Decimal("7.96") / Decimal("100") / Decimal("2")).quantize(
        Decimal("0.01")
    )
    assert entries[0].interest_component == half_year_interest
    assert entries[0].principal_component == Decimal("0.00")
    assert entries[0].closing_balance == principal
    assert entries[-1].notes == "principal_repayment_stub"
    assert entries[-1].principal_component == principal
    assert entries[-1].closing_balance == Decimal("0.00")
    await session.refresh(account)
    assert account.current_schedule_version == 2
    assert account.emi_amount == half_year_interest
