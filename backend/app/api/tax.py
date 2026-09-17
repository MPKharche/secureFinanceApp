"""Tax API endpoints."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_workspace
from app.tax.constants import CURRENT_FY
from app.tax.schemas import (
    TaxDeductionCreate,
    TaxDeductionResponse,
    TaxDeductionUpdate,
    TaxIncomeSourceCreate,
    TaxIncomeSourceResponse,
    TaxIncomeSourceUpdate,
    TaxPaymentResponse,
    TaxPaymentUpdate,
    TaxProjectionCalculateRequest,
    TaxProjectionResponse,
    WhatIfScenarioRequest,
    WhatIfScenarioResponse,
)
from app.tax.service import TaxService

router = APIRouter(prefix="/api/tax", tags=["tax"])


# Income Source Endpoints

@router.get("/income-sources/{financial_year}", response_model=Optional[TaxIncomeSourceResponse])
async def get_income_source(
    financial_year: str = CURRENT_FY,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Get income source for financial year."""
    service = TaxService(session)
    income_source = await service.get_income_source(ctx.user.id, financial_year)
    return income_source


@router.post("/income-sources", response_model=TaxIncomeSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_income_source(
    data: TaxIncomeSourceCreate,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Create or update income source."""
    service = TaxService(session)
    
    # Check if already exists
    existing = await service.get_income_source(ctx.user.id, data.financial_year)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Income source already exists for {data.financial_year}. Use PUT to update."
        )
    
    income_source = await service.update_income_source(
        ctx.user.id,
        ctx.workspace.id,
        data.financial_year,
        data.model_dump()
    )
    return income_source


@router.put("/income-sources/{financial_year}", response_model=TaxIncomeSourceResponse)
async def update_income_source(
    financial_year: str,
    data: TaxIncomeSourceUpdate,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Update income source."""
    service = TaxService(session)
    
    # Only update non-None fields
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    income_source = await service.update_income_source(
        ctx.user.id,
        ctx.workspace.id,
        financial_year,
        update_data
    )
    return income_source


# Deduction Endpoints

@router.get("/deductions/{financial_year}", response_model=Optional[TaxDeductionResponse])
async def get_deductions(
    financial_year: str = CURRENT_FY,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Get deductions for financial year."""
    service = TaxService(session)
    deductions = await service.get_deductions(ctx.user.id, financial_year)
    return deductions


@router.post("/deductions", response_model=TaxDeductionResponse, status_code=status.HTTP_201_CREATED)
async def create_deductions(
    data: TaxDeductionCreate,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Create or update deductions."""
    service = TaxService(session)
    
    # Check if already exists
    existing = await service.get_deductions(ctx.user.id, data.financial_year)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Deductions already exist for {data.financial_year}. Use PUT to update."
        )
    
    deductions = await service.update_deductions(
        ctx.user.id,
        ctx.workspace.id,
        data.financial_year,
        data.model_dump()
    )
    return deductions


@router.put("/deductions/{financial_year}", response_model=TaxDeductionResponse)
async def update_deductions(
    financial_year: str,
    data: TaxDeductionUpdate,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Update deductions."""
    service = TaxService(session)
    
    # Only update non-None fields
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    deductions = await service.update_deductions(
        ctx.user.id,
        ctx.workspace.id,
        financial_year,
        update_data
    )
    return deductions


# Tax Projection Endpoints

@router.get("/projections/{financial_year}", response_model=TaxProjectionResponse)
async def get_tax_projection(
    financial_year: str = CURRENT_FY,
    force_recalculate: bool = False,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get tax projection for financial year.
    
    Returns cached projection unless force_recalculate=true or cache is stale.
    """
    service = TaxService(session)
    
    try:
        projection_dict = await service.get_or_calculate_projection(
            ctx.user.id,
            ctx.workspace.id,
            financial_year,
            force_recalculate
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Convert dict to response schema
    return TaxProjectionResponse(
        id=UUID(projection_dict['id']),
        user_id=UUID(projection_dict['user_id']),
        workspace_id=UUID(projection_dict['workspace_id']),
        financial_year=projection_dict['financial_year'],
        old_regime=projection_dict['old_regime'],
        new_regime=projection_dict['new_regime'],
        recommended_regime=projection_dict['recommended_regime'],
        savings=projection_dict['savings'],
        tds_deducted=projection_dict['tds_deducted'],
        advance_tax_paid=projection_dict['advance_tax_paid'],
        tax_due_or_refund=projection_dict['tax_due_or_refund'],
        is_stale=projection_dict['is_stale'],
        calculated_at=projection_dict['calculated_at'],
        created_at=projection_dict['created_at'],
        updated_at=projection_dict['updated_at']
    )


@router.post("/projections/calculate", response_model=TaxProjectionResponse)
async def calculate_tax_projection(
    data: TaxProjectionCalculateRequest,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Calculate tax projection (force fresh calculation)."""
    service = TaxService(session)
    
    try:
        projection_dict = await service.calculate_and_save_projection(
            ctx.user.id,
            ctx.workspace.id,
            data.financial_year
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return TaxProjectionResponse(
        id=UUID(projection_dict['id']),
        user_id=UUID(projection_dict['user_id']),
        workspace_id=UUID(projection_dict['workspace_id']),
        financial_year=projection_dict['financial_year'],
        old_regime=projection_dict['old_regime'],
        new_regime=projection_dict['new_regime'],
        recommended_regime=projection_dict['recommended_regime'],
        savings=projection_dict['savings'],
        tds_deducted=projection_dict['tds_deducted'],
        advance_tax_paid=projection_dict['advance_tax_paid'],
        tax_due_or_refund=projection_dict['tax_due_or_refund'],
        is_stale=projection_dict['is_stale'],
        calculated_at=projection_dict['calculated_at'],
        created_at=projection_dict['created_at'],
        updated_at=projection_dict['updated_at']
    )


# What-If Scenario Endpoint

@router.post("/what-if", response_model=WhatIfScenarioResponse)
async def what_if_scenario(
    data: WhatIfScenarioRequest,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Calculate what-if tax scenario without saving.
    
    Useful for planning and comparing different income/deduction scenarios.
    """
    from decimal import Decimal
    from app.tax.engine import TaxCalculator
    
    # Get user age
    service = TaxService(session)
    user_age = await service._get_user_age(ctx.user.id)
    
    if user_age is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User date_of_birth is required for tax calculation"
        )
    
    # Prepare income data
    income_dict = {
        'salary': Decimal(str(data.income.salary_annual)),
        'rental': Decimal(str(data.income.rental_income)),
        'interest': Decimal(str(data.income.interest_income)),
        'dividend': Decimal(str(data.income.dividend_income)),
        'capital_gains_short': Decimal(str(data.income.capital_gains_short_term)),
        'capital_gains_long': Decimal(str(data.income.capital_gains_long_term)),
        'business': Decimal(str(data.income.business_income)),
        'other': Decimal(str(data.income.other_income)),
        'basic_salary': Decimal(str(data.income.basic_salary or 0)),
        'hra_received': Decimal(str(data.income.hra_received or 0))
    }
    
    # Prepare deduction data
    deduction_dict = {
        'epf_employee': Decimal(str(data.deductions.epf_employee)),
        'ppf': Decimal(str(data.deductions.ppf)),
        'elss': Decimal(str(data.deductions.elss)),
        'lic_premium': Decimal(str(data.deductions.lic_premium)),
        'nsc': Decimal(str(data.deductions.nsc)),
        'tuition_fees': Decimal(str(data.deductions.tuition_fees)),
        'principal_repayment_home_loan': Decimal(str(data.deductions.principal_repayment_home_loan)),
        'other_80c': Decimal(str(data.deductions.other_80c)),
        'nps_additional': Decimal(str(data.deductions.nps_additional)),
        'health_insurance_self': Decimal(str(data.deductions.health_insurance_self)),
        'health_insurance_parents': Decimal(str(data.deductions.health_insurance_parents)),
        'parents_are_senior_citizens': data.deductions.parents_are_senior_citizens,
        'preventive_checkup': Decimal(str(data.deductions.preventive_checkup)),
        'education_loan_interest': Decimal(str(data.deductions.education_loan_interest)),
        'donations_100_percent': Decimal(str(data.deductions.donations_100_percent)),
        'donations_50_percent': Decimal(str(data.deductions.donations_50_percent)),
        'savings_interest_claimed': Decimal(str(data.deductions.savings_interest_claimed)),
        'home_loan_interest': Decimal(str(data.deductions.home_loan_interest)),
        'property_is_self_occupied': data.deductions.property_is_self_occupied,
        'rent_paid_annual': Decimal(str(data.deductions.rent_paid_annual)),
        'city': data.deductions.city or ''
    }
    
    # Calculate
    calculator = TaxCalculator(user_age=user_age, financial_year=data.financial_year)
    result = calculator.calculate_tax(income_dict, deduction_dict)
    
    return WhatIfScenarioResponse(
        old_regime=result['old_regime'],
        new_regime=result['new_regime'],
        recommended_regime=result['recommended'],
        savings=result['savings']
    )


# TDS and Advance Tax Endpoints

@router.put("/payments/{financial_year}", response_model=TaxPaymentResponse)
async def update_tax_payments(
    financial_year: str,
    data: TaxPaymentUpdate,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Update TDS deducted and advance tax paid."""
    from sqlalchemy import select, update
    from app.models.tax import TaxProjection
    from decimal import Decimal
    
    # Get projection
    stmt = select(TaxProjection).where(
        TaxProjection.user_id == ctx.user.id,
        TaxProjection.financial_year == financial_year
    )
    result = await session.execute(stmt)
    projection = result.scalar_one_or_none()
    
    if not projection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tax projection found for {financial_year}"
        )
    
    # Update payments
    if data.tds_deducted is not None:
        projection.tds_deducted = float(data.tds_deducted)
    if data.advance_tax_paid is not None:
        projection.advance_tax_paid = float(data.advance_tax_paid)
    
    # Calculate due/refund
    recommended_tax = (
        Decimal(str(projection.old_regime_total_tax))
        if projection.recommended_regime == 'old'
        else Decimal(str(projection.new_regime_total_tax))
    )
    
    total_paid = Decimal(str(projection.tds_deducted)) + Decimal(str(projection.advance_tax_paid))
    tax_due_or_refund = total_paid - recommended_tax
    projection.tax_due_or_refund = float(tax_due_or_refund)
    
    await session.commit()
    await session.refresh(projection)
    
    # Determine status
    if tax_due_or_refund > 0:
        payment_status = "refund"
    elif tax_due_or_refund < 0:
        payment_status = "due"
    else:
        payment_status = "paid"
    
    return TaxPaymentResponse(
        financial_year=financial_year,
        tds_deducted=Decimal(str(projection.tds_deducted)),
        advance_tax_paid=Decimal(str(projection.advance_tax_paid)),
        tax_due_or_refund=tax_due_or_refund,
        recommended_regime_tax=recommended_tax,
        status=payment_status
    )


@router.get("/payments/{financial_year}", response_model=TaxPaymentResponse)
async def get_tax_payment_status(
    financial_year: str = CURRENT_FY,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Get tax payment status for financial year."""
    from sqlalchemy import select
    from app.models.tax import TaxProjection
    from decimal import Decimal
    
    stmt = select(TaxProjection).where(
        TaxProjection.user_id == ctx.user.id,
        TaxProjection.financial_year == financial_year
    )
    result = await session.execute(stmt)
    projection = result.scalar_one_or_none()
    
    if not projection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tax projection found for {financial_year}"
        )
    
    recommended_tax = (
        Decimal(str(projection.old_regime_total_tax))
        if projection.recommended_regime == 'old'
        else Decimal(str(projection.new_regime_total_tax))
    )
    
    total_paid = Decimal(str(projection.tds_deducted)) + Decimal(str(projection.advance_tax_paid))
    tax_due_or_refund = total_paid - recommended_tax
    
    if tax_due_or_refund > 0:
        payment_status = "refund"
    elif tax_due_or_refund < 0:
        payment_status = "due"
    else:
        payment_status = "paid"
    
    return TaxPaymentResponse(
        financial_year=financial_year,
        tds_deducted=Decimal(str(projection.tds_deducted)),
        advance_tax_paid=Decimal(str(projection.advance_tax_paid)),
        tax_due_or_refund=tax_due_or_refund,
        recommended_regime_tax=recommended_tax,
        status=payment_status
    )
