"""Tax service layer (business logic, caching, database operations)."""
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tax import TaxIncomeSource, TaxDeduction, TaxProjection, TaxEventLog
from app.models.user import User
from .constants import CURRENT_FY
from .engine import TaxCalculator


class TaxService:
    """Tax service with caching and database operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db
    
    async def get_or_calculate_projection(
        self,
        user_id: UUID,
        workspace_id: UUID,
        financial_year: str = CURRENT_FY,
        force_recalculate: bool = False
    ) -> Dict:
        """
        Get cached projection or calculate fresh one.
        
        Args:
            user_id: User ID
            workspace_id: Workspace ID
            financial_year: Financial year (e.g., "2026-27")
            force_recalculate: Force fresh calculation even if cache exists
        
        Returns:
            Tax projection dict with old/new regime results
        """
        # Check for cached projection
        if not force_recalculate:
            cached = await self._get_cached_projection(user_id, financial_year)
            if cached and not cached.is_stale:
                return self._projection_to_dict(cached)
        
        # Calculate fresh projection
        result = await self.calculate_and_save_projection(
            user_id, workspace_id, financial_year
        )
        return result
    
    async def calculate_and_save_projection(
        self,
        user_id: UUID,
        workspace_id: UUID,
        financial_year: str = CURRENT_FY
    ) -> Dict:
        """
        Calculate tax projection and save to database.
        
        Args:
            user_id: User ID
            workspace_id: Workspace ID
            financial_year: Financial year
        
        Returns:
            Tax projection dict
        """
        # Get user age
        user_age = await self._get_user_age(user_id)
        if user_age is None:
            raise ValueError("User date_of_birth is required for tax calculation")
        
        # Get income sources
        income_data = await self._get_income_data(user_id, financial_year)
        
        # Get deductions
        deduction_data = await self._get_deduction_data(user_id, financial_year)
        
        # Calculate tax
        calculator = TaxCalculator(user_age=user_age, financial_year=financial_year)
        result = calculator.calculate_tax(income_data, deduction_data)
        
        # Save projection
        projection = await self._save_projection(
            user_id, workspace_id, financial_year, result
        )
        
        # Log calculation event
        await self._log_event(
            user_id, financial_year, "projection_calculated",
            {"recalculated": True}
        )
        
        return self._projection_to_dict(projection)
    
    async def mark_projections_stale(
        self,
        user_id: UUID,
        financial_year: str
    ) -> None:
        """
        Mark cached projections as stale after income/deduction changes.
        
        Args:
            user_id: User ID
            financial_year: Financial year
        """
        stmt = (
            select(TaxProjection)
            .where(
                TaxProjection.user_id == user_id,
                TaxProjection.financial_year == financial_year,
                TaxProjection.is_stale == False
            )
        )
        result = await self.db.execute(stmt)
        projections = result.scalars().all()
        
        for projection in projections:
            projection.is_stale = True
        
        await self.db.commit()
    
    async def update_income_source(
        self,
        user_id: UUID,
        workspace_id: UUID,
        financial_year: str,
        income_data: Dict
    ) -> TaxIncomeSource:
        """
        Update or create income source.
        
        Args:
            user_id: User ID
            workspace_id: Workspace ID
            financial_year: Financial year
            income_data: Income data dict
        
        Returns:
            TaxIncomeSource instance
        """
        # Get existing or create new
        stmt = select(TaxIncomeSource).where(
            TaxIncomeSource.user_id == user_id,
            TaxIncomeSource.financial_year == financial_year
        )
        result = await self.db.execute(stmt)
        income_source = result.scalar_one_or_none()
        
        if income_source is None:
            income_source = TaxIncomeSource(
                user_id=user_id,
                workspace_id=workspace_id,
                financial_year=financial_year
            )
            self.db.add(income_source)
        
        # Update fields
        for key, value in income_data.items():
            if hasattr(income_source, key):
                setattr(income_source, key, value)
        
        income_source.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(income_source)
        
        # Mark projections stale
        await self.mark_projections_stale(user_id, financial_year)
        
        # Log event
        await self._log_event(
            user_id, financial_year, "income_updated", income_data
        )
        
        return income_source
    
    async def update_deductions(
        self,
        user_id: UUID,
        workspace_id: UUID,
        financial_year: str,
        deduction_data: Dict
    ) -> TaxDeduction:
        """
        Update or create deductions.
        
        Args:
            user_id: User ID
            workspace_id: Workspace ID
            financial_year: Financial year
            deduction_data: Deduction data dict
        
        Returns:
            TaxDeduction instance
        """
        # Get existing or create new
        stmt = select(TaxDeduction).where(
            TaxDeduction.user_id == user_id,
            TaxDeduction.financial_year == financial_year
        )
        result = await self.db.execute(stmt)
        deduction = result.scalar_one_or_none()
        
        if deduction is None:
            deduction = TaxDeduction(
                user_id=user_id,
                workspace_id=workspace_id,
                financial_year=financial_year
            )
            self.db.add(deduction)
        
        # Update fields
        for key, value in deduction_data.items():
            if hasattr(deduction, key):
                setattr(deduction, key, value)
        
        deduction.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(deduction)
        
        # Mark projections stale
        await self.mark_projections_stale(user_id, financial_year)
        
        # Log event
        await self._log_event(
            user_id, financial_year, "deductions_updated", deduction_data
        )
        
        return deduction
    
    async def get_income_source(
        self,
        user_id: UUID,
        financial_year: str
    ) -> Optional[TaxIncomeSource]:
        """Get income source for user and financial year."""
        stmt = select(TaxIncomeSource).where(
            TaxIncomeSource.user_id == user_id,
            TaxIncomeSource.financial_year == financial_year
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_deductions(
        self,
        user_id: UUID,
        financial_year: str
    ) -> Optional[TaxDeduction]:
        """Get deductions for user and financial year."""
        stmt = select(TaxDeduction).where(
            TaxDeduction.user_id == user_id,
            TaxDeduction.financial_year == financial_year
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    # Private helper methods
    
    async def _get_user_age(self, user_id: UUID) -> Optional[int]:
        """Calculate user age from date_of_birth."""
        stmt = select(User.date_of_birth).where(User.id == user_id)
        result = await self.db.execute(stmt)
        dob = result.scalar_one_or_none()
        
        if dob is None:
            return None
        
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    
    async def _get_income_data(
        self,
        user_id: UUID,
        financial_year: str
    ) -> Dict[str, Decimal]:
        """Get income data as dict for calculator."""
        income_source = await self.get_income_source(user_id, financial_year)
        
        if income_source is None:
            return {'salary': Decimal('0')}
        
        return {
            'salary': Decimal(str(income_source.salary_annual or 0)),
            'rental': Decimal(str(income_source.rental_income or 0)),
            'interest': Decimal(str(income_source.interest_income or 0)),
            'dividend': Decimal(str(income_source.dividend_income or 0)),
            'capital_gains_short': Decimal(str(income_source.capital_gains_short_term or 0)),
            'capital_gains_long': Decimal(str(income_source.capital_gains_long_term or 0)),
            'business': Decimal(str(income_source.business_income or 0)),
            'other': Decimal(str(income_source.other_income or 0)),
            'basic_salary': Decimal(str(income_source.basic_salary or 0)),
            'hra_received': Decimal(str(income_source.hra_received or 0))
        }
    
    async def _get_deduction_data(
        self,
        user_id: UUID,
        financial_year: str
    ) -> Dict:
        """Get deduction data as dict for calculator."""
        deduction = await self.get_deductions(user_id, financial_year)
        
        if deduction is None:
            return {}
        
        return {
            'epf_employee': Decimal(str(deduction.epf_employee or 0)),
            'ppf': Decimal(str(deduction.ppf or 0)),
            'elss': Decimal(str(deduction.elss or 0)),
            'lic_premium': Decimal(str(deduction.lic_premium or 0)),
            'nsc': Decimal(str(deduction.nsc or 0)),
            'tuition_fees': Decimal(str(deduction.tuition_fees or 0)),
            'principal_repayment_home_loan': Decimal(str(deduction.principal_repayment_home_loan or 0)),
            'other_80c': Decimal(str(deduction.other_80c or 0)),
            'nps_additional': Decimal(str(deduction.nps_additional or 0)),
            'health_insurance_self': Decimal(str(deduction.health_insurance_self or 0)),
            'health_insurance_parents': Decimal(str(deduction.health_insurance_parents or 0)),
            'parents_are_senior_citizens': deduction.parents_are_senior_citizens,
            'preventive_checkup': Decimal(str(deduction.preventive_checkup or 0)),
            'education_loan_interest': Decimal(str(deduction.education_loan_interest or 0)),
            'donations_100_percent': Decimal(str(deduction.donations_100_percent or 0)),
            'donations_50_percent': Decimal(str(deduction.donations_50_percent or 0)),
            'savings_interest_claimed': Decimal(str(deduction.savings_interest_claimed or 0)),
            'home_loan_interest': Decimal(str(deduction.home_loan_interest or 0)),
            'property_is_self_occupied': deduction.property_is_self_occupied,
            'rent_paid_annual': Decimal(str(deduction.rent_paid_annual or 0)),
            'city': deduction.city or ''
        }
    
    async def _get_cached_projection(
        self,
        user_id: UUID,
        financial_year: str
    ) -> Optional[TaxProjection]:
        """Get cached projection if exists."""
        stmt = select(TaxProjection).where(
            TaxProjection.user_id == user_id,
            TaxProjection.financial_year == financial_year
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _save_projection(
        self,
        user_id: UUID,
        workspace_id: UUID,
        financial_year: str,
        calculation_result: Dict
    ) -> TaxProjection:
        """Save or update tax projection."""
        projection = await self._get_cached_projection(user_id, financial_year)
        
        old = calculation_result['old_regime']
        new = calculation_result['new_regime']
        
        if projection is None:
            projection = TaxProjection(
                user_id=user_id,
                workspace_id=workspace_id,
                financial_year=financial_year
            )
            self.db.add(projection)
        
        # Update old regime fields
        projection.old_regime_gross_income = float(old['gross_income'])
        projection.old_regime_total_deductions = float(old['total_deductions'])
        projection.old_regime_taxable_income = float(old['taxable_income'])
        projection.old_regime_tax_liability = float(old['tax_liability'])
        projection.old_regime_cess = float(old['cess'])
        projection.old_regime_total_tax = float(old['total_tax'])
        
        # Update new regime fields
        projection.new_regime_gross_income = float(new['gross_income'])
        projection.new_regime_taxable_income = float(new['taxable_income'])
        projection.new_regime_tax_liability = float(new['tax_liability'])
        projection.new_regime_cess = float(new['cess'])
        projection.new_regime_total_tax = float(new['total_tax'])
        
        # Update recommendation
        projection.recommended_regime = calculation_result['recommended']
        projection.savings_with_recommendation = float(calculation_result['savings'])
        
        # Reset stale flag and update timestamp
        projection.is_stale = False
        projection.calculated_at = datetime.utcnow()
        projection.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(projection)
        
        return projection
    
    async def _log_event(
        self,
        user_id: UUID,
        financial_year: str,
        event_type: str,
        event_data: Dict
    ) -> None:
        """Log tax-related event."""
        event = TaxEventLog(
            user_id=user_id,
            financial_year=financial_year,
            event_type=event_type,
            event_data=event_data,
            triggered_recalculation=True
        )
        self.db.add(event)
        await self.db.commit()
    
    def _projection_to_dict(self, projection: TaxProjection) -> Dict:
        """Convert TaxProjection model to dict."""
        return {
            'id': str(projection.id),
            'user_id': str(projection.user_id),
            'workspace_id': str(projection.workspace_id),
            'financial_year': projection.financial_year,
            'old_regime': {
                'gross_income': Decimal(str(projection.old_regime_gross_income or 0)),
                'total_deductions': Decimal(str(projection.old_regime_total_deductions or 0)),
                'taxable_income': Decimal(str(projection.old_regime_taxable_income or 0)),
                'tax_liability': Decimal(str(projection.old_regime_tax_liability or 0)),
                'cess': Decimal(str(projection.old_regime_cess or 0)),
                'total_tax': Decimal(str(projection.old_regime_total_tax or 0))
            },
            'new_regime': {
                'gross_income': Decimal(str(projection.new_regime_gross_income or 0)),
                'taxable_income': Decimal(str(projection.new_regime_taxable_income or 0)),
                'tax_liability': Decimal(str(projection.new_regime_tax_liability or 0)),
                'cess': Decimal(str(projection.new_regime_cess or 0)),
                'total_tax': Decimal(str(projection.new_regime_total_tax or 0))
            },
            'recommended_regime': projection.recommended_regime,
            'savings': Decimal(str(projection.savings_with_recommendation or 0)),
            'tds_deducted': Decimal(str(projection.tds_deducted or 0)),
            'advance_tax_paid': Decimal(str(projection.advance_tax_paid or 0)),
            'tax_due_or_refund': Decimal(str(projection.tax_due_or_refund or 0)) if projection.tax_due_or_refund else None,
            'is_stale': projection.is_stale,
            'calculated_at': projection.calculated_at.isoformat() if projection.calculated_at else None,
            'created_at': projection.created_at.isoformat() if projection.created_at else None,
            'updated_at': projection.updated_at.isoformat() if projection.updated_at else None
        }
