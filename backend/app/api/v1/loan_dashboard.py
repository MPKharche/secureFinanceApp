"""Loan dashboard API endpoints."""
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_workspace
from app.services import loan_dashboard_service
from app.services import prepayment_strategy_service


router = APIRouter()


# Schemas
class DashboardSummaryResponse(BaseModel):
    total_monthly_emi: Decimal
    total_outstanding: Decimal
    principal_paid_ytd: Decimal
    interest_paid_ytd: Decimal
    active_loan_count: int
    debt_free_date: Optional[str] = None
    months_to_debt_free: int


class UpcomingPaymentResponse(BaseModel):
    schedule_entry_id: str
    loan_id: str
    loan_name: str
    due_date: str
    emi_amount: Decimal
    principal_component: Decimal
    interest_component: Decimal
    payment_status: str
    days_until_due: int


class DebtHealthRequest(BaseModel):
    monthly_income: Decimal = Field(gt=0, description="Monthly gross income")
    other_obligations: Decimal = Field(default=Decimal("0"), ge=0, description="Other monthly obligations")


class DebtHealthResponse(BaseModel):
    dti: Optional[float]
    foir: Optional[float]
    status: str
    breakdown: dict
    thresholds: dict
    recommendations: list[str]


class CompareStrategiesRequest(BaseModel):
    prepayment_amount: Decimal = Field(gt=0, description="Prepayment amount")


class CompareStrategiesResponse(BaseModel):
    strategies: list[dict]


class PriorityRankingResponse(BaseModel):
    avalanche: list[dict]
    snowball: list[dict]
    balanced: dict


class TimelineResponse(BaseModel):
    timeline: list[dict]


# Endpoints
@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Get dashboard summary with KPIs."""
    summary = await loan_dashboard_service.get_dashboard_summary(
        session=db,
        workspace_id=workspace.id,
    )
    
    # Convert date to string for JSON serialization
    if summary["debt_free_date"]:
        summary["debt_free_date"] = summary["debt_free_date"].isoformat()
    
    return summary


@router.get("/upcoming-payments", response_model=list[UpcomingPaymentResponse])
async def get_upcoming_payments(
    days: int = Query(default=30, ge=1, le=90),
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Get upcoming payments for next N days."""
    payments = await loan_dashboard_service.get_upcoming_payments(
        session=db,
        workspace_id=workspace.id,
        days=days,
    )
    
    # Convert dates to strings
    for payment in payments:
        payment["due_date"] = payment["due_date"].isoformat()
    
    return payments


@router.post("/calculate-debt-health", response_model=DebtHealthResponse)
async def calculate_debt_health(
    request: DebtHealthRequest,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Calculate debt health metrics (DTI/FOIR)."""
    return await loan_dashboard_service.calculate_debt_health(
        session=db,
        workspace_id=workspace.id,
        monthly_income=request.monthly_income,
        other_obligations=request.other_obligations,
    )


@router.post("/compare-strategies", response_model=CompareStrategiesResponse)
async def compare_strategies(
    request: CompareStrategiesRequest,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Compare prepayment strategies (Avalanche, Snowball, Balanced)."""
    return await prepayment_strategy_service.compare_strategies(
        session=db,
        workspace_id=workspace.id,
        prepayment_amount=request.prepayment_amount,
    )


@router.get("/priority-ranking", response_model=PriorityRankingResponse)
async def get_priority_ranking(
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Get priority ranking for each strategy."""
    return await prepayment_strategy_service.get_priority_ranking(
        session=db,
        workspace_id=workspace.id,
    )


@router.get("/timeline", response_model=TimelineResponse)
async def get_emi_timeline(
    months: int = Query(default=24, ge=1, le=60),
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Get month-by-month EMI timeline."""
    timeline = await loan_dashboard_service.generate_emi_timeline(
        session=db,
        workspace_id=workspace.id,
        months=months,
    )
    return {"timeline": timeline}
