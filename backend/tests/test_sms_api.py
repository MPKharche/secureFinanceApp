"""Tests for SMS API endpoints."""

import pytest
import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, AsyncMock

from httpx import AsyncClient


@pytest.mark.asyncio
class TestSMSIngestEndpoint:
    """Test SMS ingest endpoint."""

    async def test_ingest_sms_success(self, async_client: AsyncClient, auth_headers):
        """Test successful SMS ingestion."""
        payload = {
            "sender": "HDFCBK",
            "body": "INR 100.50 debited from A/c XX1234 on 17-Sep-26 at Amazon",
            "received_at": "2026-09-17T10:30:00+05:30"
        }
        
        with patch("app.tasks.sms_tasks.process_sms_task.delay") as mock_task:
            response = await async_client.post(
                "/api/sms/ingest",
                json=payload,
                headers=auth_headers,
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "sms_log_id" in data
        mock_task.assert_called_once()

    async def test_ingest_sms_duplicate(self, async_client: AsyncClient, auth_headers):
        """Test duplicate SMS detection."""
        payload = {
            "sender": "HDFCBK",
            "body": "INR 100.50 debited from A/c XX1234",
            "received_at": "2026-09-17T10:30:00+05:30"
        }
        
        # First ingestion
        with patch("app.tasks.sms_tasks.process_sms_task.delay"):
            response1 = await async_client.post(
                "/api/sms/ingest",
                json=payload,
                headers=auth_headers,
            )
        
        assert response1.status_code == 201
        sms_log_id_1 = response1.json()["sms_log_id"]
        
        # Second ingestion (duplicate)
        with patch("app.tasks.sms_tasks.process_sms_task.delay") as mock_task:
            response2 = await async_client.post(
                "/api/sms/ingest",
                json=payload,
                headers=auth_headers,
            )
        
        assert response2.status_code == 201
        data = response2.json()
        assert data["success"] is True
        assert "duplicate" in data["message"].lower()
        assert data["sms_log_id"] == sms_log_id_1
        # Task should not be called for duplicate
        mock_task.assert_not_called()

    async def test_ingest_sms_validation_error(self, async_client: AsyncClient, auth_headers):
        """Test validation error for invalid payload."""
        payload = {
            "sender": "",  # Empty sender
            "body": "Test message",
            "received_at": "2026-09-17T10:30:00+05:30"
        }
        
        response = await async_client.post(
            "/api/sms/ingest",
            json=payload,
            headers=auth_headers,
        )
        
        assert response.status_code == 422


@pytest.mark.asyncio
class TestReviewQueueEndpoints:
    """Test review queue endpoints."""

    async def test_get_review_queue_empty(self, async_client: AsyncClient, auth_headers):
        """Test getting empty review queue."""
        response = await async_client.get(
            "/api/sms/review-queue",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_get_review_queue_with_items(
        self, async_client: AsyncClient, auth_headers, async_session, test_workspace, test_user
    ):
        """Test getting review queue with items."""
        from app.models.sms_log import SMSLog
        from app.services.review_queue import add_to_review_queue
        
        # Create SMS log
        sms_log = SMSLog(
            user_id=test_user.id,
            workspace_id=test_workspace.workspace_id,
            sender="HDFCBK",
            body="Test SMS",
            received_at=datetime.now(),
            processed=False,
            processing_status="pending",
        )
        async_session.add(sms_log)
        await async_session.commit()
        await async_session.refresh(sms_log)
        
        # Add to review queue
        await add_to_review_queue(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            user_id=test_user.id,
            sms_log_id=sms_log.id,
            review_type="low_confidence",
            review_data={"confidence": 0.3},
        )
        
        # Get review queue
        response = await async_client.get(
            "/api/sms/review-queue",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["review_type"] == "low_confidence"
        assert data[0]["status"] == "pending"
        assert data[0]["sender"] == "HDFCBK"

    async def test_approve_review_item(
        self, async_client: AsyncClient, auth_headers, async_session, test_workspace, test_user
    ):
        """Test approving a review item."""
        from app.models.sms_log import SMSLog
        from app.services.review_queue import add_to_review_queue
        
        # Create SMS log and review item
        sms_log = SMSLog(
            user_id=test_user.id,
            workspace_id=test_workspace.workspace_id,
            sender="HDFCBK",
            body="Test SMS",
            received_at=datetime.now(),
            processed=False,
            processing_status="pending",
        )
        async_session.add(sms_log)
        await async_session.commit()
        await async_session.refresh(sms_log)
        
        review_item = await add_to_review_queue(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            user_id=test_user.id,
            sms_log_id=sms_log.id,
            review_type="low_confidence",
            review_data={"confidence": 0.3},
        )
        
        # Approve
        response = await async_client.post(
            f"/api/sms/review/{review_item.id}/approve",
            json={"resolution_notes": "Looks good"},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["resolution_notes"] == "Looks good"

    async def test_reject_review_item(
        self, async_client: AsyncClient, auth_headers, async_session, test_workspace, test_user
    ):
        """Test rejecting a review item."""
        from app.models.sms_log import SMSLog
        from app.services.review_queue import add_to_review_queue
        
        # Create SMS log and review item
        sms_log = SMSLog(
            user_id=test_user.id,
            workspace_id=test_workspace.workspace_id,
            sender="HDFCBK",
            body="Test SMS",
            received_at=datetime.now(),
            processed=False,
            processing_status="pending",
        )
        async_session.add(sms_log)
        await async_session.commit()
        await async_session.refresh(sms_log)
        
        review_item = await add_to_review_queue(
            db=async_session,
            workspace_id=test_workspace.workspace_id,
            user_id=test_user.id,
            sms_log_id=sms_log.id,
            review_type="failed_parse",
            review_data={"error": "Invalid format"},
        )
        
        # Reject
        response = await async_client.post(
            f"/api/sms/review/{review_item.id}/reject",
            json={"resolution_notes": "Not a transaction"},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["resolution_notes"] == "Not a transaction"

    async def test_review_item_not_found(self, async_client: AsyncClient, auth_headers):
        """Test review item not found."""
        random_id = uuid.uuid4()
        
        response = await async_client.post(
            f"/api/sms/review/{random_id}/approve",
            json={},
            headers=auth_headers,
        )
        
        assert response.status_code == 404
