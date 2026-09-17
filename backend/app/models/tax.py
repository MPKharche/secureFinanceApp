"""Tax-related SQLAlchemy models."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DECIMAL, Boolean, Date, ForeignKey, JSON, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class TaxIncomeSource(Base):
    """Income sources for tax calculation."""
    __tablename__ = 'tax_income_sources'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()')
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False
    )
    financial_year: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Income types
    salary_annual: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    rental_income: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    interest_income: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    dividend_income: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    capital_gains_short_term: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    capital_gains_long_term: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    business_income: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    other_income: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    
    # Salary breakdown for HRA
    basic_salary: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    hra_received: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    special_allowance: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    
    # Auto-detection metadata
    salary_auto_detected: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    interest_auto_detected: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    last_auto_detection_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, server_default=text('NOW()')
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text('NOW()')
    )
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="tax_income_sources")
    workspace: Mapped["Workspace"] = relationship()


class TaxDeduction(Base):
    """Tax deductions for old regime."""
    __tablename__ = 'tax_deductions'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()')
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False
    )
    financial_year: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Section 80C
    epf_employee: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    ppf: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    elss: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    lic_premium: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    nsc: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    tuition_fees: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    principal_repayment_home_loan: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    other_80c: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    
    # Section 80CCD(1B)
    nps_additional: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    
    # Section 80D
    health_insurance_self: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    health_insurance_parents: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    parents_are_senior_citizens: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    preventive_checkup: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    
    # Section 80E
    education_loan_interest: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    
    # Section 80G
    donations_100_percent: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    donations_50_percent: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    
    # Section 80TTA/TTB
    savings_interest_claimed: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    
    # Section 24(b)
    home_loan_interest: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    property_is_self_occupied: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    
    # HRA
    rent_paid_annual: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    city: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, server_default=text('NOW()')
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text('NOW()')
    )
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="tax_deductions")
    workspace: Mapped["Workspace"] = relationship()


class TaxProjection(Base):
    """Cached tax calculation results."""
    __tablename__ = 'tax_projections'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()')
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False
    )
    financial_year: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Old regime results
    old_regime_gross_income: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    old_regime_total_deductions: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    old_regime_taxable_income: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    old_regime_tax_liability: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    old_regime_cess: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    old_regime_total_tax: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    
    # New regime results
    new_regime_gross_income: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    new_regime_taxable_income: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    new_regime_tax_liability: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    new_regime_cess: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    new_regime_total_tax: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    
    # Recommendation
    recommended_regime: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    savings_with_recommendation: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    
    # TDS tracking
    tds_deducted: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    advance_tax_paid: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), default=0, server_default='0')
    tax_due_or_refund: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)
    
    # Cache metadata
    calculated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, server_default=text('NOW()')
    )
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, server_default=text('NOW()')
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text('NOW()')
    )
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="tax_projections")
    workspace: Mapped["Workspace"] = relationship()


class TaxEventLog(Base):
    """Event log for tax-related changes."""
    __tablename__ = 'tax_events_log'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()')
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False
    )
    financial_year: Mapped[str] = mapped_column(String(10), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    triggered_recalculation: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, server_default=text('NOW()')
    )
