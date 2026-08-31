"""Workspace-level MCP propose tools: accounts, transfers, payees, budgets,
goals, assets, groups. Preview + external apply, same gate as the original
transaction propose tools.
"""
import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import mcp_server.tools  # noqa: F401
from mcp_server.auth import CallContext
from mcp_server.registry import REGISTRY

pytestmark = pytest.mark.asyncio


async def test_get_transaction_by_id(session: AsyncSession, test_user, test_transactions):
    handler = REGISTRY["get_transaction"].handler
    ctx = CallContext(user_id=test_user.id)
    tx = test_transactions[0]
    r = await handler(session=session, ctx=ctx, transaction_id=str(tx.id))
    assert r["id"] == str(tx.id)
    assert r["description"] == tx.description
    assert "error" not in r


async def test_get_transaction_unknown(session: AsyncSession, test_user):
    handler = REGISTRY["get_transaction"].handler
    ctx = CallContext(user_id=test_user.id)
    r = await handler(session=session, ctx=ctx, transaction_id=str(uuid.uuid4()))
    assert r["error"] == "transaction not found"


async def test_propose_create_account_preview_and_apply(session: AsyncSession, test_user):
    from app.models.account import Account

    handler = REGISTRY["propose_create_account"].handler
    ctx = CallContext(user_id=test_user.id, external=True)
    preview = await handler(
        session=session, ctx=ctx, name="ICICI Bank", account_type="savings", currency="INR"
    )
    assert preview["kind"] == "create_account"
    assert "applied" not in preview

    applied = await handler(
        session=session,
        ctx=ctx,
        name="ICICI Bank",
        account_type="savings",
        currency="INR",
        apply=True,
    )
    assert applied.get("applied") is True
    row = (
        await session.execute(select(Account).where(Account.id == uuid.UUID(applied["id"])))
    ).scalar_one()
    assert row.name == "ICICI Bank"
    assert row.type == "savings"
    assert row.currency == "INR"


async def test_propose_close_account_delete_manual(session: AsyncSession, test_user):
    from app.models.account import Account

    handler_create = REGISTRY["propose_create_account"].handler
    handler_close = REGISTRY["propose_close_account"].handler
    ctx = CallContext(user_id=test_user.id, external=True)
    created = await handler_create(
        session=session, ctx=ctx, name="Temp Wallet", account_type="wallet", apply=True
    )
    acc_id = created["id"]
    deleted = await handler_close(
        session=session, ctx=ctx, account_id=acc_id, mode="delete", apply=True
    )
    assert deleted.get("deleted") is True
    gone = (
        await session.execute(select(Account).where(Account.id == uuid.UUID(acc_id)))
    ).scalar_one_or_none()
    assert gone is None


async def test_propose_close_account_rejects_synced_delete(
    session: AsyncSession, test_user, test_account
):
    handler = REGISTRY["propose_close_account"].handler
    ctx = CallContext(user_id=test_user.id, external=True)
    r = await handler(
        session=session, ctx=ctx, account_id=str(test_account.id), mode="delete", apply=True
    )
    assert "error" in r
    assert r.get("applied") is not True


async def test_propose_create_transfer_apply(
    session: AsyncSession, test_user, test_account
):
    from app.models.transaction import Transaction

    create_acc = REGISTRY["propose_create_account"].handler
    handler = REGISTRY["propose_create_transfer"].handler
    ctx = CallContext(user_id=test_user.id, external=True)
    dest = await create_acc(
        session=session, ctx=ctx, name="Cash", account_type="wallet", currency="BRL", apply=True
    )
    r = await handler(
        session=session,
        ctx=ctx,
        from_account_id=str(test_account.id),
        to_account_id=dest["id"],
        amount=100,
        description="Move to cash",
        apply=True,
    )
    assert r.get("applied") is True
    debit = (
        await session.execute(select(Transaction).where(Transaction.id == uuid.UUID(r["debit_id"])))
    ).scalar_one()
    assert debit.type == "debit"
    assert float(debit.amount) == 100.0
    assert debit.transfer_pair_id is not None


async def test_propose_create_transfer_internal_apply_does_not_write(
    session: AsyncSession, test_user, test_account
):
    from sqlalchemy import func
    from app.models.transaction import Transaction

    create_acc = REGISTRY["propose_create_account"].handler
    handler = REGISTRY["propose_create_transfer"].handler
    ext = CallContext(user_id=test_user.id, external=True)
    dest = await create_acc(
        session=session, ctx=ext, name="Cash2", account_type="wallet", apply=True
    )
    before = (
        await session.execute(select(func.count()).select_from(Transaction))
    ).scalar_one()
    internal = CallContext(user_id=test_user.id, external=False)
    r = await handler(
        session=session,
        ctx=internal,
        from_account_id=str(test_account.id),
        to_account_id=dest["id"],
        amount=50,
        apply=True,
    )
    assert "applied" not in r
    after = (
        await session.execute(select(func.count()).select_from(Transaction))
    ).scalar_one()
    assert after == before


async def test_propose_payee_create_update_delete(session: AsyncSession, test_user):
    from app.models.payee import Payee

    create = REGISTRY["propose_create_payee"].handler
    update = REGISTRY["propose_update_payee"].handler
    delete = REGISTRY["propose_delete_payee"].handler
    ctx = CallContext(user_id=test_user.id, external=True)
    created = await create(session=session, ctx=ctx, name="Swiggy", apply=True)
    assert created.get("applied") is True
    renamed = await update(
        session=session, ctx=ctx, payee_id=created["id"], name="Swiggy India", apply=True
    )
    assert renamed.get("applied") is True
    row = (
        await session.execute(select(Payee).where(Payee.id == uuid.UUID(created["id"])))
    ).scalar_one()
    assert row.name == "Swiggy India"
    gone = await delete(session=session, ctx=ctx, payee_id=created["id"], apply=True)
    assert gone.get("deleted") is True


async def test_propose_update_and_delete_category(session: AsyncSession, test_user):
    from app.models.category import Category

    create = REGISTRY["propose_create_category"].handler
    update = REGISTRY["propose_update_category"].handler
    delete = REGISTRY["propose_delete_category"].handler
    ctx = CallContext(user_id=test_user.id, external=True)
    created = await create(session=session, ctx=ctx, name="Subscriptions", apply=True)
    updated = await update(
        session=session, ctx=ctx, category_id=created["id"], name="OTT", apply=True
    )
    assert updated.get("applied") is True
    row = (
        await session.execute(select(Category).where(Category.id == uuid.UUID(created["id"])))
    ).scalar_one()
    assert row.name == "OTT"
    gone = await delete(session=session, ctx=ctx, category_id=created["id"], apply=True)
    assert gone.get("deleted") is True


async def test_propose_update_delete_budget(session: AsyncSession, test_user, test_categories):
    from app.models.budget import Budget

    create = REGISTRY["propose_create_budget"].handler
    update = REGISTRY["propose_update_budget"].handler
    delete = REGISTRY["propose_delete_budget"].handler
    ctx = CallContext(user_id=test_user.id, external=True)
    month = date.today().replace(day=1).isoformat()
    created = await create(
        session=session,
        ctx=ctx,
        category_id=str(test_categories[0].id),
        month=month,
        amount=2000,
        apply=True,
    )
    updated = await update(
        session=session, ctx=ctx, budget_id=created["id"], amount=2500, apply=True
    )
    assert updated.get("applied") is True
    row = (
        await session.execute(select(Budget).where(Budget.id == uuid.UUID(created["id"])))
    ).scalar_one()
    assert float(row.amount) == 2500.0
    gone = await delete(session=session, ctx=ctx, budget_id=created["id"], apply=True)
    assert gone.get("deleted") is True


async def test_propose_create_budget_redirects_to_update(
    session: AsyncSession, test_user, test_categories
):
    create = REGISTRY["propose_create_budget"].handler
    ctx = CallContext(user_id=test_user.id, external=True)
    month = date.today().replace(day=1).isoformat()
    first = await create(
        session=session,
        ctx=ctx,
        category_id=str(test_categories[0].id),
        month=month,
        amount=3500,
        apply=True,
    )
    assert first.get("applied") is True
    again = await create(
        session=session,
        ctx=ctx,
        category_id=str(test_categories[0].id),
        month=month,
        amount=4050,
        apply=True,
    )
    assert again.get("next_tool") == "propose_update_budget"
    assert again["existing_budget_id"] == first["id"]
    assert again["next_args"]["amount"] == 4050.0


async def test_propose_update_goal_add_amount(session: AsyncSession, test_user):
    from app.models.goal import Goal

    create = REGISTRY["propose_create_goal"].handler
    update = REGISTRY["propose_update_goal"].handler
    ctx = CallContext(user_id=test_user.id, external=True)
    created = await create(
        session=session, ctx=ctx, name="Emergency", target_amount=10000, apply=True
    )
    # initial_amount defaults to 0
    bumped = await update(
        session=session, ctx=ctx, goal_id=created["id"], add_amount=500, apply=True
    )
    assert bumped.get("applied") is True
    row = (
        await session.execute(select(Goal).where(Goal.id == uuid.UUID(created["id"])))
    ).scalar_one()
    assert float(row.current_amount) == 500.0


async def test_propose_create_asset_and_trade(session: AsyncSession, test_user):
    from app.models.asset import Asset
    from app.models.asset_transaction import AssetTransaction

    create = REGISTRY["propose_create_asset"].handler
    trade = REGISTRY["propose_asset_trade"].handler
    ctx = CallContext(user_id=test_user.id, external=True)
    created = await create(
        session=session,
        ctx=ctx,
        name="Gold coins",
        asset_type="valuable",
        currency="INR",
        current_value=10000,
        apply=True,
    )
    assert created.get("applied") is True
    asset = (
        await session.execute(select(Asset).where(Asset.id == uuid.UUID(created["id"])))
    ).scalar_one()
    assert asset.name == "Gold coins"
    traded = await trade(
        session=session,
        ctx=ctx,
        asset_id=created["id"],
        kind="buy",
        quantity=1,
        price=2000,
        apply=True,
    )
    assert traded.get("applied") is True
    txs = (
        await session.execute(
            select(AssetTransaction).where(AssetTransaction.asset_id == asset.id)
        )
    ).scalars().all()
    assert len(txs) >= 1


async def test_propose_group_member_and_settlement(session: AsyncSession, test_user):
    from app.models.group import GroupMember
    from app.models.group_settlement import GroupSettlement

    create_g = REGISTRY["propose_create_group"].handler
    add = REGISTRY["propose_add_group_member"].handler
    settle = REGISTRY["propose_create_settlement"].handler
    ctx = CallContext(user_id=test_user.id, external=True)
    group = await create_g(
        session=session, ctx=ctx, name="Trip friends", currency="INR", apply=True
    )
    assert group.get("applied") is True
    me = await add(
        session=session, ctx=ctx, group_id=group["id"], name="Me", is_self=True, apply=True
    )
    other = await add(
        session=session, ctx=ctx, group_id=group["id"], name="Asha", apply=True
    )
    assert me.get("applied") and other.get("applied")
    settled = await settle(
        session=session,
        ctx=ctx,
        group_id=group["id"],
        from_member_id=me["id"],
        to_member_id=other["id"],
        amount=750,
        currency="INR",
        apply=True,
    )
    assert settled.get("applied") is True
    row = (
        await session.execute(
            select(GroupSettlement).where(GroupSettlement.id == uuid.UUID(settled["id"]))
        )
    ).scalar_one()
    assert float(row.amount) == 750.0
    members = (
        await session.execute(select(GroupMember).where(GroupMember.group_id == uuid.UUID(group["id"])))
    ).scalars().all()
    assert len(members) == 2
