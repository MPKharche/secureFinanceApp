"""Pydantic schemas for tax API."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# Income Source Schemas

class TaxIncomeSourceBase(BaseModel):
    """Base schema for tax income source."""
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$", example="2026-27")
    salary_annual: Decimal = Field(default=Decimal("0"), ge=0, example=1000000)
    rental_income: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    interest_income: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    dividend_income: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    capital_gains_short_term: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    capital_gains_long_term: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    business_income: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    other_income: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    basic_salary: Optional[Decimal] = Field(default=None, ge=0, example=500000)
    hra_received: Optional[Decimal] = Field(default=None, ge=0, example=300000)
    special_allowance: Optional[Decimal] = Field(default=None, ge=0, example=200000)


class TaxIncomeSourceCreate(TaxIncomeSourceBase):
    """Schema for creating tax income source."""
    pass


class TaxIncomeSourceUpdate(BaseModel):
    """Schema for updating tax income source (all fields optional)."""
    financial_year: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")
    salary_annual: Optional[Decimal] = Field(None, ge=0)
    rental_income: Optional[Decimal] = Field(None, ge=0)
    interest_income: Optional[Decimal] = Field(None, ge=0)
    dividend_income: Optional[Decimal] = Field(None, ge=0)
    capital_gains_short_term: Optional[Decimal] = Field(None, ge=0)
    capital_gains_long_term: Optional[Decimal] = Field(None, ge=0)
    business_income: Optional[Decimal] = Field(None, ge=0)
    other_income: Optional[Decimal] = Field(None, ge=0)
    basic_salary: Optional[Decimal] = Field(None, ge=0)
    hra_received: Optional[Decimal] = Field(None, ge=0)
    special_allowance: Optional[Decimal] = Field(None, ge=0)


class TaxIncomeSourceResponse(TaxIncomeSourceBase):
    """Schema for tax income source response."""
    id: UUID
    user_id: UUID
    workspace_id: UUID
    salary_auto_detected: bool = False
    interest_auto_detected: bool = False
    last_auto_detection_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Deduction Schemas

class TaxDeductionBase(BaseModel):
    """Base schema for tax deductions."""
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$", example="2026-27")
    # Section 80C
    epf_employee: Decimal = Field(default=Decimal("0"), ge=0, example=150000)
    ppf: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    elss: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    lic_premium: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    nsc: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    tuition_fees: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    principal_repayment_home_loan: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    other_80c: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    # Section 80CCD(1B)
    nps_additional: Decimal = Field(default=Decimal("0"), ge=0, example=50000)
    # Section 80D
    health_insurance_self: Decimal = Field(default=Decimal("0"), ge=0, example=25000)
    health_insurance_parents: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    parents_are_senior_citizens: bool = Field(default=False)
    preventive_checkup: Decimal = Field(default=Decimal("0"), ge=0, example=5000)
    # Section 80E
    education_loan_interest: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    # Section 80G
    donations_100_percent: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    donations_50_percent: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    # Section 80TTA/TTB
    savings_interest_claimed: Decimal = Field(default=Decimal("0"), ge=0, example=0)
    # Section 24(b)
    home_loan_interest: Decimal = Field(default=Decimal("0"), ge=0, example=200000)
    property_is_self_occupied: bool = Field(default=True)
    # HRA
    rent_paid_annual: Decimal = Field(default=Decimal("0"), ge=0, example=240000)
    city: Optional[str] = Field(default=None, example="Mumbai")


class TaxDeductionCreate(TaxDeductionBase):
    """Schema for creating tax deductions."""
    pass


class TaxDeductionUpdate(BaseModel):
    """Schema for updating tax deductions (all fields optional)."""
    financial_year: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")
    epf_employee: Optional[Decimal] = Field(None, ge=0)
    ppf: Optional[Decimal] = Field(None, ge=0)
    elss: Optional[Decimal] = Field(None, ge=0)
    lic_premium: Optional[Decimal] = Field(None, ge=0)
    nsc: Optional[Decimal] = Field(None, ge=0)
    tuition_fees: Optional[Decimal] = Field(None, ge=0)
    principal_repayment_home_loan: Optional[Decimal] = Field(None, ge=0)
    other_80c: Optional[Decimal] = Field(None, ge=0)
    nps_additional: Optional[Decimal] = Field(None, ge=0)
    health_insurance_self: Optional[Decimal] = Field(None, ge=0)
    health_insurance_parents: Optional[Decimal] = Field(None, ge=0)
    parents_are_senior_citizens: Optional[bool] = None
    preventive_checkup: Optional[Decimal] = Field(None, ge=0)
    education_loan_interest: Optional[Decimal] = Field(None, ge=0)
    donations_100_percent: Optional[Decimal] = Field(None, ge=0)
    donations_50_percent: Optional[Decimal] = Field(None, ge=0)
    savings_interest_claimed: Optional[Decimal] = Field(None, ge=0)
    home_loan_interest: Optional[Decimal] = Field(None, ge=0)
    property_is_self_occupied: Optional[bool] = None
    rent_paid_annual: Optional[Decimal] = Field(None, ge=0)
    city: Optional[str] = None


class TaxDeductionResponse(TaxDeductionBase):
    """Schema for tax deduction response."""
    id: UUID
    user_id: UUID
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Projection Schemas

class TaxRegimeResult(BaseModel):
    """Tax calculation result for one regime."""
    gross_income: Decimal
    total_deductions: Optional[Decimal] = None
    taxable_income: Decimal
    tax_liability: Decimal
    cess: Decimal
    total_tax: Decimal


class TaxProjectionResponse(BaseModel):
    """Schema for tax projection response."""
    id: UUID
    user_id: UUID
    workspace_id: UUID
    financial_year: str
    old_regime: TaxRegimeResult
    new_regime: TaxRegimeResult
    recommended_regime: str = Field(..., pattern="^(old|new)$")
    savings: Decimal = Field(..., description="Savings with recommended regime")
    tds_deducted: Decimal = Field(default=Decimal("0"), ge=0)
    advance_tax_paid: Decimal = Field(default=Decimal("0"), ge=0)
    tax_due_or_refund: Optional[Decimal] = None
    is_stale: bool = False
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime


class TaxProjectionCalculateRequest(BaseModel):
    """Request to calculate tax projection."""
    financial_year: str = Field(default="2026-27", pattern=r"^\d{4}-\d{2}$")
    force_recalculate: bool = Field(default=False, description="Force fresh calculation")


class TaxProjectionCalculateResponse(BaseModel):
    """Response for tax projection calculation."""
    projection: TaxProjectionResponse
    cache_hit: bool = Field(..., description="Whether result was from cache")


# What-If Scenario Schemas

class WhatIfScenarioRequest(BaseModel):
    """Request for what-if tax scenario."""
    financial_year: str = Field(default="2026-27", pattern=r"^\d{4}-\d{2}$")
    income: TaxIncomeSourceBase
    deductions: TaxDeductionBase


class WhatIfScenarioResponse(BaseModel):
    """Response for what-if scenario."""
    old_regime: TaxRegimeResult
    new_regime: TaxRegimeResult
    recommended_regime: str
    savings: Decimal
    comparison_with_current: Optional[dict] = Field(
        default=None,
        description="Comparison with user's current projection if exists"
    )


# TDS and Advance Tax Schemas

class TaxPaymentUpdate(BaseModel):
    """Schema for updating TDS and advance tax."""
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    tds_deducted: Optional[Decimal] = Field(None, ge=0)
    advance_tax_paid: Optional[Decimal] = Field(None, ge=0)


class TaxPaymentResponse(BaseModel):
    """Response for tax payment status."""
    financial_year: str
    tds_deducted: Decimal
    advance_tax_paid: Decimal
    tax_due_or_refund: Decimal
    recommended_regime_tax: Decimal
    status: str = Field(..., description="due, refund, or paid")


# Event Log Schemas

class TaxEventLogResponse(BaseModel):
    """Schema for tax event log."""
    id: UUID
    user_id: UUID
    financial_year: str
    event_type: str
    event_data: Optional[dict] = None
    triggered_recalculation: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
