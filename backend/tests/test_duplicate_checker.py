"""Tests for duplicate detection service."""

import pytest
import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.services.duplicate_checker import check_duplicate, check_duplicate_fuzzy
from app.models.transaction import Transaction


@pytest.mark.asyncio
class TestDuplicateChecker:
    """Test duplicate detection."""

    async def test_check_duplicate_exact_match(self, session, test_workspace, test_account):
        """Test exact duplicate detection - same amount, date, account."""
        # Create existing transaction
        existing = Transaction(
            user_id=test_workspace.user_id,
            workspace_id=test_workspace.id,
            account_id=test_account.id,
            amount=Decimal("-100.50"),
            currency="INR",
            date=date(2026, 9, 17),
            effective_date=date(2026, 9, 17),
            description="Test transaction",
            type="debit",
            source="manual",
        )
        session.add(existing)
        await session.commit()

        # Check for duplicate
        duplicate = await check_duplicate(
            db=session,
            workspace_id=test_workspace.id,
            amount=Decimal("100.50"),  # Absolute value
            transaction_date=date(2026, 9, 17),
            account_id=test_account.id,
        )

        assert duplicate is not None
        assert duplicate.id == existing.id

    async def test_check_duplicate_no_match(self, session, test_workspace, test_account):
        """Test no duplicate when amount differs."""
        # Create existing transaction
        existing = Transaction(
            user_id=test_workspace.user_id,
            workspace_id=test_workspace.id,
            account_id=test_account.id,
            amount=Decimal("-100.50"),
            currency="INR",
            date=date(2026, 9, 17),
            effective_date=date(2026, 9, 17),
            description="Test transaction",
            type="debit",
            source="manual",
        )
        session.add(existing)
        await session.commit()

        # Check for duplicate with different amount
        duplicate = await check_duplicate(
            db=session,
            workspace_id=test_workspace.id,
            amount=Decimal("200.00"),  # Different amount
            transaction_date=date(2026, 9, 17),
            account_id=test_account.id,
        )

        assert duplicate is None

    async def test_check_duplicate_different_day(self, session, test_workspace, test_account):
        """Test no duplicate when date differs."""
        # Create existing transaction
        existing = Transaction(
            user_id=test_workspace.user_id,
            workspace_id=test_workspace.id,
            account_id=test_account.id,
            amount=Decimal("-100.50"),
            currency="INR",
            date=date(2026, 9, 17),
            effective_date=date(2026, 9, 17),
            description="Test transaction",
            type="debit",
            source="manual",
        )
        session.add(existing)
        await session.commit()

        # Check for duplicate on different day
        duplicate = await check_duplicate(
            db=session,
            workspace_id=test_workspace.id,
            amount=Decimal("100.50"),
            transaction_date=date(2026, 9, 18),  # Different date
            account_id=test_account.id,
        )

        assert duplicate is None

    async def test_check_duplicate_fuzzy_within_tolerance(self, session, test_workspace, test_account):
        """Test fuzzy duplicate detection within tolerance."""
        # Create existing transaction
        existing = Transaction(
            user_id=test_workspace.user_id,
            workspace_id=test_workspace.id,
            account_id=test_account.id,
            amount=Decimal("-100.50"),
            currency="INR",
            date=date(2026, 9, 17),
            effective_date=date(2026, 9, 17),
            description="Purchase at Amazon",
            type="debit",
            source="manual",
        )
        session.add(existing)
        await session.commit()

        # Check fuzzy duplicate with slight amount variance
        duplicates = await check_duplicate_fuzzy(
            db=session,
            workspace_id=test_workspace.id,
            amount=Decimal("100.51"),  # 0.01 difference
            transaction_date=date(2026, 9, 17),
            merchant="Amazon",
            tolerance_amount=Decimal("0.05"),
            tolerance_days=1,
        )

        assert len(duplicates) == 1
        assert duplicates[0].id == existing.id

    async def test_check_duplicate_fuzzy_outside_tolerance(self, session, test_workspace, test_account):
        """Test fuzzy duplicate detection outside tolerance."""
        # Create existing transaction
        existing = Transaction(
            user_id=test_workspace.user_id,
            workspace_id=test_workspace.id,
            account_id=test_account.id,
            amount=Decimal("-100.50"),
            currency="INR",
            date=date(2026, 9, 17),
            effective_date=date(2026, 9, 17),
            description="Purchase at Amazon",
            type="debit",
            source="manual",
        )
        session.add(existing)
        await session.commit()

        # Check fuzzy duplicate with large amount variance
        duplicates = await check_duplicate_fuzzy(
            db=session,
            workspace_id=test_workspace.id,
            amount=Decimal("150.00"),  # 49.50 difference
            transaction_date=date(2026, 9, 17),
            merchant="Amazon",
            tolerance_amount=Decimal("0.05"),
            tolerance_days=1,
        )

        assert len(duplicates) == 0

    async def test_check_duplicate_fuzzy_date_tolerance(self, session, test_workspace, test_account):
        """Test fuzzy duplicate with date tolerance."""
        # Create existing transaction
        existing = Transaction(
            user_id=test_workspace.user_id,
            workspace_id=test_workspace.id,
            account_id=test_account.id,
            amount=Decimal("-100.50"),
            currency="INR",
            date=date(2026, 9, 17),
            effective_date=date(2026, 9, 17),
            description="Purchase at Amazon",
            type="debit",
            source="manual",
        )
        session.add(existing)
        await session.commit()

        # Check fuzzy duplicate next day (within tolerance)
        duplicates = await check_duplicate_fuzzy(
            db=session,
            workspace_id=test_workspace.id,
            amount=Decimal("100.50"),
            transaction_date=date(2026, 9, 18),  # 1 day later
            merchant="Amazon",
            tolerance_amount=Decimal("0.01"),
            tolerance_days=1,
        )

        assert len(duplicates) == 1
        assert duplicates[0].id == existing.id
