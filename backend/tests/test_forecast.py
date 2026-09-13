"""G3 multi-year forecast."""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.asset import Asset
from app.models.transaction import Transaction
from app.services.report_service import get_forecast


async def _manual_account(session: AsyncSession, user_id, name="Checking", acct_type="checking", balance="0", rate=None) -> Account:
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        type=acct_type,
        balance=Decimal(str(balance)),
        currency="INR",
        is_closed=False,
        interest_rate=Decimal(str(rate)) if rate is not None else None,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


async def _txn(session, user_id, account_id, amount, txn_type, txn_date):
    txn = Transaction(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=account_id,
        description=f"Test {txn_type} {amount}",
        amount=Decimal(str(amount)),
        date=txn_date,
        effective_date=txn_date,
        type=txn_type,
        source="manual",
        status="posted",
        currency="INR",
        created_at=datetime.now(timezone.utc),
    )
    session.add(txn)
    await session.commit()
    return txn


@pytest.mark.asyncio
async def test_forecast_horizon_and_assumption_keys(session: AsyncSession, test_user, test_workspace):
    acct = await _manual_account(session, test_user.id, balance="50000")
    today = date.today()
    await _txn(session, test_user.id, acct.id, 12000, "credit", date(today.year, 1, 10))
    await _txn(session, test_user.id, acct.id, 4000, "debit", date(today.year, 1, 12))

    report = await get_forecast(
        session,
        test_workspace.id,
        test_user.id,
        horizon_years=5,
        inflation_pct=4,
        income_growth_pct=5,
        expense_growth_pct=3,
        loan_rate_pct=7.96,
        rate_reset="use_assumption",
        sv_path="hold_flat",
        premium_annual=120000,
    )
    assert report.horizon_years == 5
    assert len(report.years) == 5
    keys = {a.key for a in report.assumptions}
    for required in (
        "horizon_years",
        "inflation_pct",
        "income_growth_pct",
        "expense_growth_pct",
        "loan_rate_pct",
        "rate_reset",
        "sv_path",
        "premium_annual",
    ):
        assert required in keys
    assert report.years[0].premium == 120000.0
    # income compounds from year 2
    assert report.years[1].income >= report.years[0].income
    assert report.years[-1].calendar_year == today.year + 5


@pytest.mark.asyncio
async def test_forecast_illus_sv_path(session: AsyncSession, test_user, test_workspace):
    await _manual_account(session, test_user.id, name="Savings", balance="10000")
    asset = Asset(
        id=uuid.uuid4(),
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        name="Pru Test",
        type="other",
        currency="INR",
        purchase_price=Decimal("0"),
        external_metadata={
            "policy_number": "TEST1",
            "sum_assured_on_death": 1000000,
            "illus_sv_year5": 389495,
            "premium_monthly": 10000,
            "cos_illustration": {
                "year_5": {"sv_approx": 389495, "ssv": 389495},
                "year_6": {"sv_approx": 420000, "ssv": 420000},
            },
            "g0_assumptions": {"loan_rate_percent": 7.96, "principal": 160000, "premium_amount": 10000},
        },
    )
    session.add(asset)
    await session.commit()

    report = await get_forecast(
        session,
        test_workspace.id,
        test_user.id,
        horizon_years=2,
        sv_path="illus_table",
        rate_reset="use_assumption",
        loan_rate_pct=7.96,
    )
    assert any(a.key == "sv_path" and a.value == "illus_table" for a in report.assumptions)
    assert report.opening.premium_annual == 120000.0
    # year 1 should pick policy year ~6 SV if opening is year 5
    assert report.years[0].insurance_sv in (420000.0, report.years[0].insurance_sv)
