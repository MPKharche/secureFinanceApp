"""G2 profit & loss YTD + annual projection."""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import Transaction
from app.services.report_service import get_profit_loss


async def _manual_account(session: AsyncSession, user_id, name="Checking") -> Account:
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        type="checking",
        balance=Decimal("0"),
        currency="BRL",
        is_closed=False,
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
        currency="BRL",
        created_at=datetime.now(timezone.utc),
    )
    session.add(txn)
    await session.commit()
    return txn


@pytest.mark.asyncio
async def test_profit_loss_ytd_and_run_rate(session: AsyncSession, test_user, test_workspace):
    acct = await _manual_account(session, test_user.id)
    today = date.today()
    ytd_day = date(today.year, 1, 15) if today >= date(today.year, 1, 15) else today

    await _txn(session, test_user.id, acct.id, 3000, "credit", ytd_day)
    await _txn(session, test_user.id, acct.id, 1000, "debit", ytd_day)

    report = await get_profit_loss(
        session,
        test_workspace.id,
        test_user.id,
        year=today.year,
        income_growth_pct=0,
        expense_growth_pct=0,
        include_tax=False,
    )
    assert report.year == today.year
    assert report.totals.ytd_income == 3000.0
    assert report.totals.ytd_expenses == 1000.0
    assert report.totals.ytd_net == 2000.0
    assert report.projection_method in ("run_rate", "schedules")
    assert report.totals.projected_income >= report.totals.ytd_income
    assert any(a.key == "income_growth_pct" for a in report.assumptions)
    assert "G3" in " ".join(report.gaps)


@pytest.mark.asyncio
async def test_profit_loss_tax_and_growth(session: AsyncSession, test_user, test_workspace):
    acct = await _manual_account(session, test_user.id, name="Income Acct")
    today = date.today()
    await _txn(session, test_user.id, acct.id, 3650, "credit", date(today.year, 1, 2))

    report = await get_profit_loss(
        session,
        test_workspace.id,
        test_user.id,
        year=today.year,
        income_growth_pct=10,
        expense_growth_pct=0,
        include_tax=True,
        effective_tax_rate=20,
    )
    assert report.totals.projected_income >= report.totals.ytd_income
    assert any(a.key == "include_tax" and a.value == "yes" for a in report.assumptions)
    if report.totals.projected_net > 0 and report.totals.projected_tax > 0:
        assert report.totals.projected_net_after_tax == round(
            report.totals.projected_net - report.totals.projected_tax, 2
        )
