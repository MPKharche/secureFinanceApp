"""Capital gains calculator API endpoints."""
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_workspace
from app.tax.capital_gains_engine import CapitalGain, CapitalGainsSummary, CapitalGainsTaxEngine

router = APIRouter(prefix="/api/capital-gains", tags=["capital-gains"])


# Request/Response Schemas
class AssetSale(BaseModel):
    """Single asset sale for capital gains calculation."""
    asset_name: str = Field(..., min_length=1, max_length=200)
    asset_type: str = Field(..., description="equity, mutual_fund, debt, real_estate, gold, crypto")
    buy_date: date
    sell_date: date
    buy_price: Decimal = Field(..., gt=0)
    sell_price: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)


class CalculateCapitalGainsRequest(BaseModel):
    """Request to calculate capital gains."""
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$", example="2026-27")
    sales: List[AssetSale] = Field(..., min_items=1)
    user_income_tax_slab_rate: Optional[Decimal] = Field(
        default=Decimal("0.30"), 
        ge=0, 
        le=1,
        description="User's income tax slab rate (for debt STCG). Default 30%"
    )


class CapitalGainResponse(BaseModel):
    """Single capital gain calculation result."""
    asset_name: str
    asset_type: str
    buy_date: date
    sell_date: date
    buy_price: Decimal
    sell_price: Decimal
    quantity: Decimal
    gain_loss: Decimal
    holding_period_days: int
    classification: str  # STCG or LTCG
    asset_class: str  # equity or debt
    tax_rate: Decimal
    tax_amount: Decimal


class CapitalGainsSummaryResponse(BaseModel):
    """Summary of all capital gains."""
    financial_year: str
    equity_stcg_total: Decimal
    equity_stcg_tax: Decimal
    equity_ltcg_total: Decimal
    equity_ltcg_exempt: Decimal
    equity_ltcg_taxable: Decimal
    equity_ltcg_tax: Decimal
    debt_stcg_total: Decimal
    debt_ltcg_total: Decimal
    debt_ltcg_tax: Decimal
    total_gains: Decimal
    total_tax: Decimal
    cess: Decimal
    total_tax_with_cess: Decimal
    advance_tax_required: bool
    advance_tax_schedule: List[dict]


class CalculateCapitalGainsResponse(BaseModel):
    """Complete capital gains calculation response."""
    gains: List[CapitalGainResponse]
    summary: CapitalGainsSummaryResponse


class TaxHarvestingSuggestion(BaseModel):
    """Tax harvesting suggestion."""
    asset_name: str
    asset_type: str
    unrealized_loss: Decimal
    action: str
    tax_savings: Decimal


class CurrentHolding(BaseModel):
    """Current holding for tax harvesting analysis."""
    asset_name: str
    asset_type: str
    unrealized_loss: Decimal


class TaxHarvestingRequest(BaseModel):
    """Request for tax harvesting suggestions."""
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    realized_gains: List[AssetSale]
    current_holdings: List[CurrentHolding]


class TaxHarvestingResponse(BaseModel):
    """Tax harvesting suggestions response."""
    suggestions: List[TaxHarvestingSuggestion]
    total_potential_savings: Decimal


@router.post("/calculate", response_model=CalculateCapitalGainsResponse)
async def calculate_capital_gains(
    request: CalculateCapitalGainsRequest,
    workspace: WorkspaceContext = Depends(current_workspace),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Calculate capital gains tax for asset sales.
    
    - Supports equity and debt assets
    - Classifies as STCG/LTCG based on holding period
    - Applies correct tax rates per asset class
    - Calculates advance tax schedule if applicable
    """
    # Initialize engine with user's tax slab
    engine = CapitalGainsTaxEngine(user_income_tax_slab_rate=request.user_income_tax_slab_rate)
    
    # Calculate individual gains
    gains: List[CapitalGain] = []
    for sale in request.sales:
        gain = engine.calculate_single_gain(
            asset_name=sale.asset_name,
            asset_type=sale.asset_type,
            buy_date=sale.buy_date,
            sell_date=sale.sell_date,
            buy_price=sale.buy_price,
            sell_price=sale.sell_price,
            quantity=sale.quantity,
        )
        gains.append(gain)
    
    # Aggregate summary
    summary = engine.aggregate_gains(gains, request.financial_year)
    
    # Convert to response models
    gains_response = [
        CapitalGainResponse(
            asset_name=g.asset_name,
            asset_type=g.asset_type,
            buy_date=g.buy_date,
            sell_date=g.sell_date,
            buy_price=g.buy_price,
            sell_price=g.sell_price,
            quantity=g.quantity,
            gain_loss=g.gain_loss,
            holding_period_days=g.holding_period_days,
            classification=g.classification,
            asset_class=g.asset_class,
            tax_rate=g.tax_rate,
            tax_amount=g.tax_amount,
        )
        for g in gains
    ]
    
    summary_response = CapitalGainsSummaryResponse(
        financial_year=summary.financial_year,
        equity_stcg_total=summary.equity_stcg_total,
        equity_stcg_tax=summary.equity_stcg_tax,
        equity_ltcg_total=summary.equity_ltcg_total,
        equity_ltcg_exempt=summary.equity_ltcg_exempt,
        equity_ltcg_taxable=summary.equity_ltcg_taxable,
        equity_ltcg_tax=summary.equity_ltcg_tax,
        debt_stcg_total=summary.debt_stcg_total,
        debt_ltcg_total=summary.debt_ltcg_total,
        debt_ltcg_tax=summary.debt_ltcg_tax,
        total_gains=summary.total_gains,
        total_tax=summary.total_tax,
        cess=summary.cess,
        total_tax_with_cess=summary.total_tax_with_cess,
        advance_tax_required=summary.advance_tax_required,
        advance_tax_schedule=summary.advance_tax_schedule,
    )
    
    return CalculateCapitalGainsResponse(
        gains=gains_response,
        summary=summary_response,
    )


@router.post("/tax-harvesting", response_model=TaxHarvestingResponse)
async def suggest_tax_harvesting(
    request: TaxHarvestingRequest,
    workspace: WorkspaceContext = Depends(current_workspace),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Suggest tax loss harvesting opportunities.
    
    Analyzes realized gains and suggests which holdings with unrealized losses
    should be sold to offset gains and reduce tax liability.
    """
    engine = CapitalGainsTaxEngine()
    
    # Calculate realized gains
    gains: List[CapitalGain] = []
    for sale in request.realized_gains:
        gain = engine.calculate_single_gain(
            asset_name=sale.asset_name,
            asset_type=sale.asset_type,
            buy_date=sale.buy_date,
            sell_date=sale.sell_date,
            buy_price=sale.buy_price,
            sell_price=sale.sell_price,
            quantity=sale.quantity,
        )
        gains.append(gain)
    
    # Convert holdings to dict format expected by engine
    holdings_dict = [
        {
            "asset_name": h.asset_name,
            "asset_type": h.asset_type,
            "unrealized_loss": float(h.unrealized_loss),
        }
        for h in request.current_holdings
    ]
    
    # Get suggestions
    suggestions_raw = engine.suggest_tax_harvesting(gains, holdings_dict)
    
    # Convert to response model
    suggestions = [
        TaxHarvestingSuggestion(
            asset_name=s["asset_name"],
            asset_type=s["asset_type"],
            unrealized_loss=Decimal(str(s["unrealized_loss"])),
            action=s["action"],
            tax_savings=Decimal(str(s["tax_savings"])),
        )
        for s in suggestions_raw
    ]
    
    total_savings = sum(s.tax_savings for s in suggestions)
    
    return TaxHarvestingResponse(
        suggestions=suggestions,
        total_potential_savings=total_savings,
    )
