import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_workspace
from app.schemas.report import BalanceSheetResponse, ForecastResponse, ProfitLossResponse, ReportResponse
from app.services import report_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/net-worth", response_model=ReportResponse)
async def get_net_worth(
    months: int = Query(12, ge=1, le=24),
    interval: str = Query("monthly", pattern="^(daily|weekly|monthly|yearly)$"),
    account_ids: Optional[list[uuid.UUID]] = Query(None),
    asset_group_ids: Optional[list[uuid.UUID]] = Query(None),
    period: str | None = Query(None, pattern="^ytd$"),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return await report_service.get_net_worth_report(
        session, ctx.workspace.id, ctx.user_id, months, interval, ctx.user.primary_currency,
        account_ids=account_ids, asset_group_ids=asset_group_ids, period=period,
    )


@router.get("/income-expenses", response_model=ReportResponse)
async def get_income_expenses(
    months: int = Query(12, ge=1, le=24),
    interval: str = Query("monthly", pattern="^(daily|weekly|monthly|yearly)$"),
    account_ids: Optional[list[uuid.UUID]] = Query(None),
    period: str | None = Query(None, pattern="^ytd$"),
    days: Optional[int] = Query(None, ge=1, le=730),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """`days` overrides `months` with an exact rolling window ending today."""
    return await report_service.get_income_expenses_report(
        session, ctx.workspace.id, ctx.user_id, months, interval, ctx.user.primary_currency,
        account_ids=account_ids, period=period, days=days,
    )


@router.get("/cash-flow", response_model=ReportResponse)
async def get_cash_flow(
    months: int = Query(6, ge=1, le=12),
    interval: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    baseline: bool = Query(False),
    account_ids: Optional[list[uuid.UUID]] = Query(None),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return await report_service.get_cash_flow_report(
        session, ctx.workspace.id, ctx.user_id, months, interval, ctx.user.primary_currency,
        baseline=baseline, account_ids=account_ids,
    )


@router.get("/balance-sheet", response_model=BalanceSheetResponse)
async def get_balance_sheet(
    as_of: Optional[str] = Query(None, description="ISO date YYYY-MM-DD; default today"),
    insurance_value_basis: str = Query(
        "recorded",
        pattern="^(recorded|sad|sv)$",
        description="Insurance valuation: recorded AssetValue, SAD, or illustrative SV",
    ),
    account_ids: Optional[list[uuid.UUID]] = Query(None),
    asset_group_ids: Optional[list[uuid.UUID]] = Query(None),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    from datetime import date as date_cls

    cutoff = None
    if as_of:
        try:
            cutoff = date_cls.fromisoformat(as_of)
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="as_of must be YYYY-MM-DD")
    return await report_service.get_balance_sheet(
        session,
        ctx.workspace.id,
        ctx.user_id,
        cutoff,
        insurance_value_basis=insurance_value_basis,
        account_ids=account_ids,
        asset_group_ids=asset_group_ids,
    )


@router.get("/profit-loss", response_model=ProfitLossResponse)
async def get_profit_loss(
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Calendar year; default current"),
    income_growth_pct: float = Query(0.0, ge=-100, le=500, description="G4-lite annual income growth %"),
    expense_growth_pct: float = Query(0.0, ge=-100, le=500, description="G4-lite annual expense growth %"),
    include_tax: bool = Query(False, description="Apply simple effective tax on projected net"),
    effective_tax_rate: float = Query(0.0, ge=0, le=100, description="Effective tax rate % when include_tax"),
    account_ids: Optional[list[uuid.UUID]] = Query(None),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return await report_service.get_profit_loss(
        session,
        ctx.workspace.id,
        ctx.user_id,
        year=year,
        income_growth_pct=income_growth_pct,
        expense_growth_pct=expense_growth_pct,
        include_tax=include_tax,
        effective_tax_rate=effective_tax_rate,
        account_ids=account_ids,
    )



@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    horizon_years: int = Query(5, ge=1, le=30, description="G3 forecast horizon in years"),
    inflation_pct: float = Query(0.0, ge=-50, le=100, description="G4 annual inflation %"),
    income_growth_pct: float = Query(0.0, ge=-100, le=500, description="G4 income growth path %"),
    expense_growth_pct: float = Query(0.0, ge=-100, le=500, description="G4 expense growth path %"),
    loan_rate_pct: float | None = Query(None, ge=0, le=100, description="Policy loan rate % assumption"),
    rate_reset: str = Query(
        "none",
        pattern="^(none|use_assumption)$",
        description="none=account rate when set; use_assumption=apply loan_rate_pct",
    ),
    sv_path: str = Query(
        "illus_table",
        pattern="^(illus_table|hold_flat|live)$",
        description="SV path: CoS illus table, hold flat, or live (fallback)",
    ),
    premium_annual: float | None = Query(None, ge=0, description="Override annual premium; default from schedules/metadata"),
    account_ids: Optional[list[uuid.UUID]] = Query(None),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return await report_service.get_forecast(
        session,
        ctx.workspace.id,
        ctx.user_id,
        horizon_years=horizon_years,
        inflation_pct=inflation_pct,
        income_growth_pct=income_growth_pct,
        expense_growth_pct=expense_growth_pct,
        loan_rate_pct=loan_rate_pct,
        rate_reset=rate_reset,
        sv_path=sv_path,
        premium_annual=premium_annual,
        account_ids=account_ids,
    )
