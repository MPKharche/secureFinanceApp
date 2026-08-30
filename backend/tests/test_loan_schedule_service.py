from datetime import date, timedelta
from decimal import Decimal
import pytest
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.loan_schedule_service import calculate_emi, generate_amortization_schedule
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
