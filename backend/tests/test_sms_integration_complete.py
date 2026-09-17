"""Tests for SMS auto-capture integration."""
import pytest
from datetime import datetime
from decimal import Decimal
import uuid

from app.models.sms_log import SMSLog
from app.models.sms_review_queue import SMSReviewQueue
from app.models.transaction import Transaction


@pytest.mark.asyncio
async def test_sms_ingest_endpoint(async_client, auth_headers, test_workspace):
    """Test SMS ingest endpoint."""
    payload = {
        "sender": "HDFCBK",
        "body": "INR 1250.50 debited from A/c XX1234 on 17-Sep-26 at Amazon",
        "received_at": "2026-09-17T10:30:00Z",
    }
    
    response = await async_client.post(
        "/api/sms/ingest",
        json=payload,
        headers=auth_headers,
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "sms_log_id" in data


@pytest.mark.asyncio
async def test_sms_ingest_idempotency(async_client, auth_headers, test_workspace):
    """Test idempotency check for duplicate SMS."""
    payload = {
        "sender": "ICICIB",
        "body": "Rs.500 sent to Merchant via UPI",
        "received_at": "2026-09-17T11:00:00Z",
    }
    
    # First request
    response1 = await async_client.post(
        "/api/sms/ingest",
        json=payload,
        headers=auth_headers,
    )
    assert response1.status_code == 201
    sms_id_1 = response1.json()["sms_log_id"]
    
    # Second identical request
    response2 = await async_client.post(
        "/api/sms/ingest",
        json=payload,
        headers=auth_headers,
    )
    assert response2.status_code == 201
    data2 = response2.json()
    assert "duplicate" in data2["message"].lower()
    assert data2["sms_log_id"] == sms_id_1


@pytest.mark.asyncio
async def test_sms_parser_with_llm(async_session):
    """Test SMS parser with LLM."""
    from app.services.sms_parser import parse_sms_with_llm
    
    sender = "HDFCBK"
    body = "INR 1500.00 debited from A/c XX5678 on 17-SEP-26 at SWIGGY"
    user_id = str(uuid.uuid4())
    
    result = await parse_sms_with_llm(sender, body, user_id)
    
    # Should successfully parse or fail gracefully
    assert result is not None
    assert hasattr(result, 'confidence')
    assert hasattr(result, 'success')


@pytest.mark.asyncio
async def test_duplicate_checker(async_session, test_workspace, test_user, test_account):
    """Test duplicate transaction detection."""
    from app.services.duplicate_checker import check_duplicate
    
    # Create existing transaction
    existing = Transaction(
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        account_id=test_account.id,
        amount=Decimal("-1500.00"),
        date=datetime(2026, 9, 17).date(),
        description="Test transaction",
        currency="INR",
        type="debit",
    )
    async_session.add(existing)
    await async_session.commit()
    
    # Check for duplicate
    duplicate = await check_duplicate(
        db=async_session,
        workspace_id=test_workspace.id,
        amount=Decimal("1500.00"),
        transaction_date=datetime(2026, 9, 17).date(),
        account_id=test_account.id,
    )
    
    assert duplicate is not None
    assert duplicate.id == existing.id


@pytest.mark.asyncio
async def test_review_queue_get_pending(async_client, auth_headers, test_workspace, test_user):
    """Test fetching review queue."""
    response = await async_client.get(
        "/api/sms/review-queue?status=pending",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_review_queue_approve(async_session, test_workspace, test_user):
    """Test approving review queue item."""
    from app.services.review_queue import add_to_review_queue, approve_review_item
    
    # Create SMS log
    sms_log = SMSLog(
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        sender="TEST",
        body="Test SMS",
        received_at=datetime.now(),
        processed=False,
    )
    async_session.add(sms_log)
    await async_session.commit()
    await async_session.refresh(sms_log)
    
    # Add to review queue
    review_item = await add_to_review_queue(
        db=async_session,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        sms_log_id=sms_log.id,
        review_type="low_confidence",
        review_data={"confidence": 0.3},
    )
    
    assert review_item.status == "pending"
    
    # Approve
    approved = await approve_review_item(
        db=async_session,
        review_id=review_item.id,
        resolved_by=test_user.id,
        resolution_notes="Manually verified",
    )
    
    assert approved.status == "approved"
    assert approved.resolved_by == test_user.id


@pytest.mark.asyncio
async def test_category_learning(async_session, test_workspace, test_category):
    """Test merchant category learning."""
    from app.services.category_learning import learn_merchant_category, get_category_for_merchant
    
    # Learn mapping
    mapping = await learn_merchant_category(
        db=async_session,
        workspace_id=test_workspace.id,
        merchant="Amazon India",
        category_id=test_category.id,
    )
    
    assert mapping.merchant_name_normalized == "amazon india"
    assert mapping.category_id == test_category.id
    
    # Retrieve mapping
    found_category = await get_category_for_merchant(
        db=async_session,
        workspace_id=test_workspace.id,
        merchant="AMAZON INDIA",  # Different case
    )
    
    assert found_category == test_category.id


@pytest.mark.asyncio
async def test_sms_review_queue_filter_by_type(async_client, auth_headers):
    """Test filtering review queue by type."""
    response = await async_client.get(
        "/api/sms/review-queue?status=pending&review_type=duplicate",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # All items should be duplicates if any exist
    if len(data) > 0:
        assert all(item["review_type"] == "duplicate" for item in data)
