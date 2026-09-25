"""G1 balance sheet as-of date."""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.asset import Asset
from app.models.asset_value import AssetValue
from app.models.transaction import Transaction
from app.services.report_service import get_balance_sheet


async def _manual_account(session: AsyncSession, user_id, name="Savings", acct_type="savings") -> Account:
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        type=acct_type,
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
async def test_balance_sheet_as_of_manual_account(session: AsyncSession, test_user, test_workspace):
    acct = await _manual_account(session, test_user.id)
    today = date.today()
    older = today - timedelta(days=10)
    await _txn(session, test_user.id, acct.id, 10000, "credit", older)
    await _txn(session, test_user.id, acct.id, 1000, "credit", today)

    past = await get_balance_sheet(
        session, test_workspace.id, test_user.id, older, insurance_value_basis="recorded"
    )
    assert past.as_of == older.isoformat()
    cash = [l for l in past.lines if l.group == "cash_accounts"]
    assert len(cash) == 1
    assert cash[0].value == 10000.0
    assert cash[0].fidelity == "as_of"
    assert past.totals.net_worth == 10000.0

    now = await get_balance_sheet(session, test_workspace.id, test_user.id, today)
    cash_now = [l for l in now.lines if l.group == "cash_accounts"]
    assert cash_now[0].value == 11000.0


@pytest.mark.asyncio
async def test_balance_sheet_insurance_sv_vs_sad(session: AsyncSession, test_user, test_workspace):
    asset = Asset(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="ICICI Pru GIFT Test",
        type="other",
        currency="BRL",
        external_metadata={
            "policy_number": "A8884526",
            "sum_assured_on_death": 1200000,
            "illus_sv_year5": 389495,
        },
    )
    session.add(asset)
    await session.flush()
    session.add(
        AssetValue(
            id=uuid.uuid4(),
            asset_id=asset.id,
            amount=Decimal("1200000"),
            date=date.today(),
        )
    )
    await session.commit()

    sad = await get_balance_sheet(
        session, test_workspace.id, test_user.id, date.today(), insurance_value_basis="sad"
    )
    inv = [l for l in sad.lines if l.group == "investments"]
    assert len(inv) == 1
    assert inv[0].value == 1200000.0

    sv = await get_balance_sheet(
        session, test_workspace.id, test_user.id, date.today(), insurance_value_basis="sv"
    )
    inv_sv = [l for l in sv.lines if l.group == "investments"]
    assert inv_sv[0].value == 389495.0
    assert inv_sv[0].fidelity == "approx_current"
    assert any(a.key == "insurance_value_basis" and a.value == "sv" for a in sv.assumptions)
    assert "G2" in " ".join(sv.gaps)


@pytest.mark.asyncio
async def test_balance_sheet_sv_from_g4_assumptions_map(session: AsyncSession, test_user, test_workspace):
    asset = Asset(
        id=uuid.uuid4(),
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        name="ICICI Pru GIFT",
        type="other",
        currency="INR",
        external_metadata={
            "assumptions": {
                "pru_policy_id": "A8884526",
                "pru_sv_illustrative": 389495,
                "insurance_value_basis": "sv",
            },
            "assumption_meta": {
                "pru_sv_illustrative": {
                    "status": "placeholder",
                    "label": "SV illustrative — not live quote",
                }
            },
        },
    )
    session.add(asset)
    await session.commit()

    report = await get_balance_sheet(
        session, test_workspace.id, test_user.id, date.today(), insurance_value_basis="sv"
    )
    inv = [l for l in report.lines if l.group == "investments"]
    assert len(inv) == 1
    assert inv[0].value == 389495.0
    assert inv[0].meta["sv_illustrative"] == 389495.0


@pytest.mark.asyncio
async def test_balance_sheet_sv_placeholder_not_silent_zero(
    session: AsyncSession, test_user, test_workspace
):
    asset = Asset(
        id=uuid.uuid4(),
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        name="ICICI Pru GIFT",
        type="other",
        currency="INR",
        external_metadata={
            "assumptions": {"pru_policy_id": "A8884526", "insurance_value_basis": "sv"},
            "assumption_meta": {
                "pru_sv_illustrative": {
                    "status": "placeholder",
                    "label": "Awaiting live SV quote",
                }
            },
        },
    )
    session.add(asset)
    await session.commit()

    report = await get_balance_sheet(
        session, test_workspace.id, test_user.id, date.today(), insurance_value_basis="sv"
    )
    inv = [l for l in report.lines if l.group == "investments"]
    assert len(inv) == 1
    assert inv[0].value == 0.0
    assert inv[0].meta["placeholder"] is True
    assert "Awaiting" in inv[0].fidelity_note


@pytest.mark.asyncio
async def test_balance_sheet_exclude_policy_loan_via_wiring(
    session: AsyncSession, test_user, test_workspace
):
    loan = Account(
        id=uuid.uuid4(),
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        name="Pru policy loan",
        type="loan",
        balance=Decimal("174805"),
        currency="INR",
        is_closed=False,
    )
    session.add(loan)
    await session.flush()
    await _txn(session, test_user.id, loan.id, 174805, "debit", date.today())
    asset = Asset(
        id=uuid.uuid4(),
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        name="Pru asset",
        type="other",
        currency="INR",
        external_metadata={
            "assumptions": {"include_policy_loan": False},
            "g0_wiring": {"loan_account_id": str(loan.id)},
        },
    )
    session.add(asset)
    await session.commit()

    included = await get_balance_sheet(
        session, test_workspace.id, test_user.id, date.today(), include_policy_loan=True
    )
    excluded = await get_balance_sheet(
        session, test_workspace.id, test_user.id, date.today(), include_policy_loan=False
    )
    assert included.totals.loans >= 174805.0
    assert excluded.totals.loans == 0.0


@pytest.mark.asyncio
async def test_balance_sheet_nrp_glossary_placeholder(session: AsyncSession, test_user, test_workspace):
    asset = Asset(
        id=uuid.uuid4(),
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        name="Finance assumptions",
        type="other",
        currency="INR",
        external_metadata={
            "assumptions": {
                "nrp_loan_id_label": "TBPUN00006895113",
                "las_outstanding": None,
            },
            "assumption_meta": {
                "las_outstanding": {
                    "status": "placeholder",
                    "label": "LAS O/S — awaiting statement",
                }
            },
        },
    )
    session.add(asset)
    await session.commit()

    report = await get_balance_sheet(session, test_workspace.id, test_user.id, date.today())
    las = [l for l in report.lines if l.key == "glossary:las_outstanding"]
    assert len(las) == 1
    assert las[0].meta["placeholder"] is True
    assert "LAS" in las[0].fidelity_note
