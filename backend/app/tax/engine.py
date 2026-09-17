"""Tax calculation engine (pure functions, no database access)."""
from decimal import Decimal
from typing import Dict, List, Tuple

from .constants import (
    CESS_RATE,
    HRA_METRO_PERCENT,
    HRA_NON_METRO_PERCENT,
    METRO_CITIES,
    NEW_REGIME_SLABS,
    OLD_REGIME_SLABS,
    SECTION_24B_LIMIT,
    SECTION_80C_LIMIT,
    SECTION_80CCD_1B_LIMIT,
    SECTION_80D_PARENTS_LIMIT,
    SECTION_80D_SELF_LIMIT,
    SECTION_80D_SENIOR_LIMIT,
    SECTION_80TTA_LIMIT,
    SECTION_80TTB_LIMIT,
    SECTION_87A_INCOME_LIMIT_NEW,
    SECTION_87A_INCOME_LIMIT_OLD,
    SECTION_87A_REBATE_NEW,
    SECTION_87A_REBATE_OLD,
    SENIOR_CITIZEN_AGE,
    SENIOR_CITIZEN_SLABS,
    STANDARD_DEDUCTION_NEW_REGIME,
    STANDARD_DEDUCTION_OLD_REGIME,
    SUPER_SENIOR_CITIZEN_AGE,
    SUPER_SENIOR_CITIZEN_SLABS,
)


class TaxCalculator:
    """Pure tax calculation engine (no database access)."""
    
    def __init__(self, user_age: int, financial_year: str = "2026-27"):
        """Initialize calculator with user age."""
        self.user_age = user_age
        self.financial_year = financial_year
        self.is_senior = user_age >= SENIOR_CITIZEN_AGE
        self.is_super_senior = user_age >= SUPER_SENIOR_CITIZEN_AGE
    
    def calculate_tax(
        self, income: Dict[str, Decimal], deductions: Dict[str, Decimal]
    ) -> Dict:
        """
        Calculate tax in both regimes, recommend cheaper option.
        
        Args:
            income: Dict with keys like 'salary', 'rental', 'interest', etc.
            deductions: Dict with keys like 'epf_employee', 'ppf', 'rent_paid_annual', etc.
        
        Returns:
            {
                'old_regime': {...},
                'new_regime': {...},
                'recommended': 'old' or 'new',
                'savings': Decimal
            }
        """
        old_result = self._calculate_old_regime(income, deductions)
        new_result = self._calculate_new_regime(income)
        
        if old_result['total_tax'] < new_result['total_tax']:
            recommended = 'old'
            savings = new_result['total_tax'] - old_result['total_tax']
        else:
            recommended = 'new'
            savings = old_result['total_tax'] - new_result['total_tax']
        
        return {
            'old_regime': old_result,
            'new_regime': new_result,
            'recommended': recommended,
            'savings': savings
        }
    
    def _sum_all_income(self, income: Dict) -> Decimal:
        """Sum all income sources."""
        return sum([
            income.get('salary', Decimal(0)),
            income.get('rental', Decimal(0)),
            income.get('interest', Decimal(0)),
            income.get('dividend', Decimal(0)),
            income.get('capital_gains_short', Decimal(0)),
            income.get('capital_gains_long', Decimal(0)),
            income.get('business', Decimal(0)),
            income.get('other', Decimal(0))
        ])
    
    def _apply_slabs(self, taxable_income: Decimal, slabs: List[Tuple]) -> Decimal:
        """Apply progressive tax slabs."""
        tax = Decimal(0)
        
        for lower, upper, rate in slabs:
            if taxable_income <= lower:
                break
            taxable_in_slab = min(taxable_income, Decimal(upper)) - Decimal(lower)
            tax += taxable_in_slab * Decimal(rate)
        
        return tax
    
    def _calculate_new_regime(self, income: Dict) -> Dict:
        """New regime: Higher basic exemption, no deductions except standard."""
        gross_income = self._sum_all_income(income)
        
        # Only standard deduction
        total_deductions = Decimal(STANDARD_DEDUCTION_NEW_REGIME)
        taxable_income = max(Decimal(0), gross_income - total_deductions)
        
        # Apply new slabs
        tax_liability = self._apply_slabs(taxable_income, NEW_REGIME_SLABS)
        
        # Section 87A rebate (income ≤ ₹12L)
        if taxable_income <= SECTION_87A_INCOME_LIMIT_NEW:
            rebate = min(tax_liability, Decimal(SECTION_87A_REBATE_NEW))
            tax_liability -= rebate
        
        cess = tax_liability * Decimal(CESS_RATE)
        total_tax = tax_liability + cess
        
        return {
            'gross_income': gross_income,
            'total_deductions': total_deductions,
            'taxable_income': taxable_income,
            'tax_liability': tax_liability,
            'cess': cess,
            'total_tax': total_tax
        }
    
    def _calculate_old_regime(self, income: Dict, deductions: Dict) -> Dict:
        """Old regime: Allows all deductions."""
        gross_income = self._sum_all_income(income)
        total_deductions = self._calculate_deductions_old(income, deductions)
        taxable_income = max(Decimal(0), gross_income - total_deductions)
        
        # Apply slabs based on age
        if self.is_super_senior:
            slabs = SUPER_SENIOR_CITIZEN_SLABS
        elif self.is_senior:
            slabs = SENIOR_CITIZEN_SLABS
        else:
            slabs = OLD_REGIME_SLABS
        
        tax_liability = self._apply_slabs(taxable_income, slabs)
        
        # Section 87A rebate (income ≤ ₹5L)
        if taxable_income <= SECTION_87A_INCOME_LIMIT_OLD:
            rebate = min(tax_liability, Decimal(SECTION_87A_REBATE_OLD))
            tax_liability -= rebate
        
        cess = tax_liability * Decimal(CESS_RATE)
        total_tax = tax_liability + cess
        
        return {
            'gross_income': gross_income,
            'total_deductions': total_deductions,
            'taxable_income': taxable_income,
            'tax_liability': tax_liability,
            'cess': cess,
            'total_tax': total_tax
        }
    
    def _calculate_deductions_old(self, income: Dict, deductions: Dict) -> Decimal:
        """Calculate all deductions for old regime (with limits)."""
        total = Decimal(0)
        
        # 1. Standard deduction
        total += Decimal(STANDARD_DEDUCTION_OLD_REGIME)
        
        # 2. Section 80C (max ₹1.5L)
        sec_80c = sum([
            deductions.get('epf_employee', Decimal(0)),
            deductions.get('ppf', Decimal(0)),
            deductions.get('elss', Decimal(0)),
            deductions.get('lic_premium', Decimal(0)),
            deductions.get('nsc', Decimal(0)),
            deductions.get('tuition_fees', Decimal(0)),
            deductions.get('principal_repayment_home_loan', Decimal(0)),
            deductions.get('other_80c', Decimal(0))
        ])
        total += min(sec_80c, Decimal(SECTION_80C_LIMIT))
        
        # 3. Section 80CCD(1B) - Additional NPS
        nps_add = deductions.get('nps_additional', Decimal(0))
        total += min(nps_add, Decimal(SECTION_80CCD_1B_LIMIT))
        
        # 4. Section 80D - Health insurance
        health_self = deductions.get('health_insurance_self', Decimal(0))
        health_parents = deductions.get('health_insurance_parents', Decimal(0))
        preventive = deductions.get('preventive_checkup', Decimal(0))
        parents_senior = deductions.get('parents_are_senior_citizens', False)
        
        sec_80d_self = min(health_self + preventive, Decimal(SECTION_80D_SELF_LIMIT))
        parent_limit = SECTION_80D_SENIOR_LIMIT if parents_senior else SECTION_80D_PARENTS_LIMIT
        sec_80d_parents = min(health_parents, Decimal(parent_limit))
        total += sec_80d_self + sec_80d_parents
        
        # 5. Section 80E - Education loan interest (no limit)
        total += deductions.get('education_loan_interest', Decimal(0))
        
        # 6. Section 80G - Donations
        donations_100 = deductions.get('donations_100_percent', Decimal(0))
        donations_50 = deductions.get('donations_50_percent', Decimal(0))
        total += donations_100 + (donations_50 * Decimal(0.5))
        
        # 7. Section 80TTA/TTB - Savings interest
        savings_int = deductions.get('savings_interest_claimed', Decimal(0))
        int_limit = SECTION_80TTB_LIMIT if self.is_senior else SECTION_80TTA_LIMIT
        total += min(savings_int, Decimal(int_limit))
        
        # 8. Section 24(b) - Home loan interest
        home_int = deductions.get('home_loan_interest', Decimal(0))
        is_self = deductions.get('property_is_self_occupied', True)
        if is_self:
            total += min(home_int, Decimal(SECTION_24B_LIMIT))
        else:
            total += home_int
        
        # 9. HRA exemption
        hra = self._calculate_hra_exemption(income, deductions)
        total += hra
        
        return total
    
    def _calculate_hra_exemption(self, income: Dict, deductions: Dict) -> Decimal:
        """
        HRA exemption = min of:
        1. Actual HRA received
        2. Rent paid - 10% of basic
        3. 50% of basic (metro) or 40% (non-metro)
        """
        hra_received = income.get('hra_received', Decimal(0))
        rent_paid = deductions.get('rent_paid_annual', Decimal(0))
        basic = income.get('basic_salary', Decimal(0))
        city = deductions.get('city', '')
        
        if hra_received == 0 or rent_paid == 0:
            return Decimal(0)
        
        option_1 = hra_received
        option_2 = rent_paid - (basic * Decimal('0.1'))
        is_metro = city in METRO_CITIES
        metro_pct = HRA_METRO_PERCENT if is_metro else HRA_NON_METRO_PERCENT
        option_3 = basic * Decimal(str(metro_pct))
        
        hra_exemption = min(option_1, option_2, option_3)
        return max(Decimal(0), hra_exemption)
