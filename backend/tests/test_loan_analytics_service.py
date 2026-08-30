from datetime import date
from decimal import Decimal
import pytest
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.loan_analytics_service import (
    get_loan_overview,
    get_yearly_breakdown,
    calculate_debt_ratios,
    get_dashboard_summary,
)
from app.services.loan_schedule_service import generate_amortization_schedule
from app.models.account import Account


@pytest.mark.asyncio
async def test_get_loan_overview(session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID):
    """Test loan overview metrics calculation."""
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

    overview = await get_loan_overview(session, account.id)

    assert overview["original_principal"] == 100000.00
    assert overview["current_outstanding"] == 100000.00
    assert overview["principal_paid"] == 0.00
    assert overview["interest_paid"] == 0.00
    assert overview["progress_pct"] == 0.00
    assert overview["emis_paid"] == 0
    assert overview["emis_remaining"] == 12


@pytest.mark.asyncio
async def test_get_yearly_breakdown(session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID):
    """Test yearly principal vs interest breakdown."""
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Multi-year Loan",
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

    breakdown = await get_yearly_breakdown(session, account.id, group_by="year")

    assert len(breakdown) == 5  # 60 months = 5 years
    assert breakdown[0]["period"] == "2026"
    assert breakdown[0]["emis_scheduled"] == 12
    assert breakdown[0]["principal_component"] > 0
    assert breakdown[0]["interest_component"] > 0


@pytest.mark.asyncio
async def test_calculate_debt_ratios(session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID):
    """Test debt ratio calculations."""
    # Create two loan accounts
    loan1 = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Home Loan",
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
    loan2 = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        name="Car Loan",
        type="loan",
        balance=Decimal("200000.00"),
        currency="USD",
        original_principal=Decimal("200000.00"),
        interest_rate=Decimal("10.00"),
        tenure_months=36,
        emi_amount=Decimal("6454.99"),
        disbursed_on=date(2026, 1, 1),
        emi_day=10,
        current_schedule_version=1,
    )
    session.add_all([loan1, loan2])
    await session.commit()

    await generate_amortization_schedule(session, loan1.id)
    await generate_amortization_schedule(session, loan2.id)

    # Calculate ratios with monthly income
    ratios = await calculate_debt_ratios(
        session, workspace_id, loan_ids=[loan1.id, loan2.id], monthly_income=Decimal("50000.00")
    )

    assert ratios["aggregate_metrics"]["total_outstanding"] == 700000.00
    assert ratios["aggregate_metrics"]["total_monthly_emi"] > 16000.00
    assert ratios["debt_ratios"]["debt_to_income_ratio"] < 1.0
    assert ratios["debt_ratios"]["emi_to_income_ratio"] < 1.0
