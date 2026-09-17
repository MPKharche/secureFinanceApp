"""Tests for loan dashboard service."""
import pytest
from datetime import date, timedelta
from decimal import Decimal
import uuid

from app.services import loan_dashboard_service


@pytest.mark.asyncio
async def test_get_dashboard_summary(async_session, test_workspace, test_user):
    """Test dashboard summary KPIs."""
    from app.models.account import Account
    
    # Create test loan account
    loan = Account(
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        name="Home Loan",
        account_type="loan",
        currency="INR",
        is_closed=False,
    )
    async_session.add(loan)
    await async_session.commit()
    await async_session.refresh(loan)
    
    summary = await loan_dashboard_service.get_dashboard_summary(
        session=async_session,
        workspace_id=test_workspace.id,
    )
    
    assert "total_monthly_emi" in summary
    assert "total_outstanding" in summary
    assert "active_loan_count" in summary
    assert summary["active_loan_count"] >= 1


@pytest.mark.asyncio
async def test_get_upcoming_payments(async_session, test_workspace, test_user):
    """Test upcoming payments retrieval."""
    from app.models.account import Account
    from app.models.loan_schedule import LoanSchedule
    
    # Create loan
    loan = Account(
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        name="Car Loan",
        account_type="loan",
        currency="INR",
        is_closed=False,
    )
    async_session.add(loan)
    await async_session.commit()
    await async_session.refresh(loan)
    
    # Create upcoming payment
    today = date.today()
    schedule_entry = LoanSchedule(
        loan_id=loan.id,
        due_date=today + timedelta(days=7),
        emi_amount=Decimal("5000"),
        principal_component=Decimal("3000"),
        interest_component=Decimal("2000"),
        payment_status="unpaid",
    )
    async_session.add(schedule_entry)
    await async_session.commit()
    
    payments = await loan_dashboard_service.get_upcoming_payments(
        session=async_session,
        workspace_id=test_workspace.id,
        days=30,
    )
    
    assert len(payments) >= 1
    assert payments[0]["loan_name"] == "Car Loan"
    assert payments[0]["days_until_due"] == 7


@pytest.mark.asyncio
async def test_calculate_debt_health_good(async_session, test_workspace):
    """Test debt health calculation - good status."""
    health = await loan_dashboard_service.calculate_debt_health(
        session=async_session,
        workspace_id=test_workspace.id,
        monthly_income=Decimal("100000"),
        other_obligations=Decimal("0"),
    )
    
    assert "dti" in health
    assert "foir" in health
    assert "status" in health
    assert "recommendations" in health


@pytest.mark.asyncio
async def test_calculate_debt_health_high(async_session, test_workspace, test_user):
    """Test debt health calculation - high debt."""
    from app.models.account import Account
    from app.models.loan_schedule import LoanSchedule
    
    # Create loan with high EMI
    loan = Account(
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        name="High EMI Loan",
        account_type="loan",
        currency="INR",
        is_closed=False,
    )
    async_session.add(loan)
    await async_session.commit()
    await async_session.refresh(loan)
    
    # Add schedule with high EMI
    today = date.today()
    schedule = LoanSchedule(
        loan_id=loan.id,
        due_date=today + timedelta(days=5),
        emi_amount=Decimal("50000"),  # High EMI
        principal_component=Decimal("30000"),
        interest_component=Decimal("20000"),
        payment_status="unpaid",
    )
    async_session.add(schedule)
    await async_session.commit()
    
    health = await loan_dashboard_service.calculate_debt_health(
        session=async_session,
        workspace_id=test_workspace.id,
        monthly_income=Decimal("80000"),  # Lower than EMI
        other_obligations=Decimal("10000"),
    )
    
    # Should be high risk
    assert health["status"] in ["moderate", "high"]
    assert health["foir"] > 0.5  # Over 50%


@pytest.mark.asyncio
async def test_generate_emi_timeline(async_session, test_workspace):
    """Test EMI timeline generation."""
    timeline = await loan_dashboard_service.generate_emi_timeline(
        session=async_session,
        workspace_id=test_workspace.id,
        months=12,
    )
    
    assert len(timeline) == 12
    assert all("month" in entry for entry in timeline)
    assert all("total_emi" in entry for entry in timeline)
    assert all("total_principal" in entry for entry in timeline)
    assert all("total_interest" in entry for entry in timeline)


@pytest.mark.asyncio
async def test_loan_dashboard_api_summary(async_client, auth_headers):
    """Test loan dashboard summary API endpoint."""
    response = await async_client.get(
        "/api/v1/loans/dashboard/summary",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "total_monthly_emi" in data
    assert "total_outstanding" in data
    assert "active_loan_count" in data
    assert "debt_free_date" in data


@pytest.mark.asyncio
async def test_loan_dashboard_api_upcoming_payments(async_client, auth_headers):
    """Test upcoming payments API endpoint."""
    response = await async_client.get(
        "/api/v1/loans/dashboard/upcoming-payments?days=30",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_loan_dashboard_api_debt_health(async_client, auth_headers):
    """Test debt health calculation API endpoint."""
    payload = {
        "monthly_income": 100000,
        "other_obligations": 5000,
    }
    
    response = await async_client.post(
        "/api/v1/loans/dashboard/calculate-debt-health",
        json=payload,
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "dti" in data
    assert "foir" in data
    assert "status" in data
    assert data["status"] in ["good", "moderate", "high", "unknown"]


@pytest.mark.asyncio
async def test_loan_dashboard_api_timeline(async_client, auth_headers):
    """Test EMI timeline API endpoint."""
    response = await async_client.get(
        "/api/v1/loans/dashboard/timeline?months=12",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "timeline" in data
    assert isinstance(data["timeline"], list)
