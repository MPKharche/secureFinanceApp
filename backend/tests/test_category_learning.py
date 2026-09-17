"""Tests for category learning service."""

import pytest
import uuid
from datetime import datetime, timezone

from app.services.category_learning import (
    normalize_merchant_name,
    get_category_for_merchant,
    learn_merchant_category,
)
from app.models.merchant_mapping import MerchantMapping


class TestNormalizeMerchantName:
    """Test merchant name normalization."""

    def test_normalize_basic(self):
        """Test basic normalization."""
        assert normalize_merchant_name("Amazon") == "amazon"
        assert normalize_merchant_name("AMAZON") == "amazon"
        assert normalize_merchant_name("  Amazon  ") == "amazon"

    def test_normalize_remove_suffixes(self):
        """Test removing company suffixes."""
        assert normalize_merchant_name("Acme Pvt. Ltd.") == "acme"
        assert normalize_merchant_name("Acme Private Limited") == "acme"
        assert normalize_merchant_name("Acme Ltd") == "acme"
        assert normalize_merchant_name("Acme Inc.") == "acme"
        assert normalize_merchant_name("Acme LLC") == "acme"

    def test_normalize_special_characters(self):
        """Test removing special characters."""
        assert normalize_merchant_name("Amazon.com") == "amazoncom"
        assert normalize_merchant_name("Café@Home") == "cafehome"
        assert normalize_merchant_name("Big-Bazaar") == "big-bazaar"

    def test_normalize_whitespace(self):
        """Test normalizing whitespace."""
        assert normalize_merchant_name("Big   Bazaar") == "big bazaar"
        assert normalize_merchant_name("  Big\tBazaar\n") == "big bazaar"

    def test_normalize_empty(self):
        """Test empty merchant name."""
        assert normalize_merchant_name("") == ""
        assert normalize_merchant_name("   ") == ""


@pytest.mark.asyncio
class TestCategoryLearning:
    """Test category learning functionality."""

    async def test_get_category_new_merchant(self, async_session, test_workspace):
        """Test getting category for new merchant returns None."""
        category_id = await get_category_for_merchant(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            merchant="Amazon",
        )
        
        assert category_id is None

    async def test_learn_and_get_merchant_category(self, async_session, test_workspace, test_category):
        """Test learning and retrieving merchant category."""
        # Learn merchant-category mapping
        mapping = await learn_merchant_category(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            merchant="Amazon",
            category_id=test_category.id,
        )
        
        assert mapping.merchant_name_normalized == "amazon"
        assert mapping.category_id == test_category.id
        assert mapping.transaction_count == 1
        
        # Retrieve learned category
        category_id = await get_category_for_merchant(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            merchant="Amazon",
        )
        
        assert category_id == test_category.id

    async def test_learn_updates_existing_mapping(self, async_session, test_workspace, test_category):
        """Test that learning updates existing mapping."""
        # Create initial mapping
        initial = await learn_merchant_category(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            merchant="Amazon",
            category_id=test_category.id,
        )
        
        assert initial.transaction_count == 1
        
        # Learn again with same category
        updated = await learn_merchant_category(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            merchant="Amazon",
            category_id=test_category.id,
        )
        
        assert updated.id == initial.id
        assert updated.transaction_count == 2

    async def test_learn_case_insensitive(self, async_session, test_workspace, test_category):
        """Test that learning is case-insensitive."""
        # Learn with uppercase
        await learn_merchant_category(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            merchant="AMAZON",
            category_id=test_category.id,
        )
        
        # Retrieve with lowercase
        category_id = await get_category_for_merchant(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            merchant="amazon",
        )
        
        assert category_id == test_category.id
        
        # Retrieve with mixed case
        category_id = await get_category_for_merchant(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            merchant="AmAzOn",
        )
        
        assert category_id == test_category.id

    async def test_get_category_updates_stats(self, async_session, test_workspace, test_category):
        """Test that getting category updates usage stats."""
        # Learn mapping
        mapping = await learn_merchant_category(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            merchant="Amazon",
            category_id=test_category.id,
        )
        
        original_count = mapping.transaction_count
        original_last_used = mapping.last_used_at
        
        # Wait a moment
        import asyncio
        await asyncio.sleep(0.1)
        
        # Get category (should update stats)
        await get_category_for_merchant(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            merchant="Amazon",
        )
        
        # Refresh to get updated stats
        await async_session.refresh(mapping)
        
        assert mapping.transaction_count == original_count + 1
        assert mapping.last_used_at > original_last_used

    async def test_workspace_isolation(self, async_session, test_workspace, test_category, second_workspace):
        """Test that merchant mappings are workspace-isolated."""
        # Learn in first workspace
        await learn_merchant_category(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            merchant="Amazon",
            category_id=test_category.id,
        )
        
        # Try to get from second workspace
        category_id = await get_category_for_merchant(
            db=async_session,
            workspace_id=second_workspace.workspace_id,
            merchant="Amazon",
        )
        
        assert category_id is None
