"""Test tax calculation engine."""
import pytest
from decimal import Decimal

from app.tax.engine import TaxCalculator


def test_new_regime_no_deductions():
    """Income ₹10L, new regime → Tax calculation."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1000000')}
    result = calc._calculate_new_regime(income)
    
    # 10L - 75K std deduction = 9.25L taxable
    # 0-4L: 0, 4-8L: 20K, 8-9.25L: 12.5K = 32.5K
    # Section 87A rebate applies (income < 12L): min(32.5K, 60K) = 32.5K
    # Final tax after rebate: 0
    assert result['taxable_income'] == Decimal('925000')
    assert result['tax_liability'] == Decimal('0')  # After Section 87A rebate
    assert result['cess'] == Decimal('0')
    assert result['total_tax'] == Decimal('0')


def test_old_regime_with_80c():
    """Income ₹8L, 80C ₹1.5L → Tax lower than new regime."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('800000')}
    deductions = {
        'epf_employee': Decimal('150000'),
        'rent_paid_annual': Decimal('0')
    }
    result = calc._calculate_old_regime(income, deductions)
    
    # 8L - 50K std - 1.5L 80C = 6L taxable
    # 0-2.5L: 0, 2.5-5L @ 5%: 12.5K, 5-6L @ 20%: 20K = 32.5K + cess (1.3K) = 33.8K
    assert result['total_deductions'] == Decimal('200000')
    assert result['taxable_income'] == Decimal('600000')
    # Round to handle floating point precision
    assert result['tax_liability'].quantize(Decimal('1')) == Decimal('32500')
    assert result['total_tax'].quantize(Decimal('1')) == Decimal('33800')


def test_section_87a_rebate_new_regime():
    """Income ₹7L in new regime → Section 87A rebate should apply."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('700000')}
    result = calc._calculate_new_regime(income)
    
    # Taxable: 7L - 75K = 6.25L (within ₹12L limit)
    # Tax before rebate: (4-6.25L)*5% = 11.25K
    # Rebate reduces to 0 (rebate is min(tax, 60K))
    assert result['taxable_income'] == Decimal('625000')
    assert result['tax_liability'] == Decimal('0')  # After rebate
    assert result['total_tax'] == Decimal('0')


def test_section_87a_rebate_old_regime():
    """Income ₹4.5L in old regime → Section 87A rebate should apply."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('450000')}
    deductions = {}
    result = calc._calculate_old_regime(income, deductions)
    
    # Taxable: 4.5L - 50K = 4L (within ₹5L limit)
    # Tax before rebate: (2.5-4L)*5% = 7.5K
    # Rebate is min(7.5K, 12.5K) = 7.5K → tax = 0
    assert result['taxable_income'] == Decimal('400000')
    assert result['tax_liability'] == Decimal('0')


def test_senior_citizen_slabs():
    """65-year-old gets ₹3L basic exemption in old regime."""
    calc = TaxCalculator(user_age=65)
    income = {'salary': Decimal('350000')}
    deductions = {}
    result = calc._calculate_old_regime(income, deductions)
    
    # 3.5L - 50K std = 3L taxable (senior slab: 0-3L free)
    assert result['taxable_income'] == Decimal('300000')
    assert result['tax_liability'] == Decimal('0')
    assert result['total_tax'] == Decimal('0')


def test_super_senior_citizen_slabs():
    """85-year-old gets ₹5L basic exemption in old regime."""
    calc = TaxCalculator(user_age=85)
    income = {'salary': Decimal('550000')}
    deductions = {}
    result = calc._calculate_old_regime(income, deductions)
    
    # 5.5L - 50K std = 5L taxable (super senior slab: 0-5L free)
    assert result['taxable_income'] == Decimal('500000')
    assert result['tax_liability'] == Decimal('0')
    assert result['total_tax'] == Decimal('0')


def test_80c_limit_capping():
    """80C investments of ₹2.3L should be capped at ₹1.5L."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1000000')}
    deductions = {
        'epf_employee': Decimal('100000'),
        'ppf': Decimal('100000'),
        'elss': Decimal('130000')  # Total 3.3L
    }
    result = calc._calculate_old_regime(income, deductions)
    
    # Should include only 1.5L from 80C + 50K std = 2L total
    assert result['total_deductions'] == Decimal('200000')


def test_hra_exemption_metro():
    """HRA exemption for metro city."""
    calc = TaxCalculator(user_age=30)
    income = {
        'salary': Decimal('1000000'),
        'basic_salary': Decimal('500000'),
        'hra_received': Decimal('300000')
    }
    deductions = {
        'rent_paid_annual': Decimal('400000'),
        'city': 'Mumbai'
    }
    hra = calc._calculate_hra_exemption(income, deductions)
    
    # min(30L, 40L-50K, 50% of 5L) = min(30L, 35L, 2.5L) = 2.5L
    assert hra == Decimal('250000')


def test_hra_exemption_non_metro():
    """HRA exemption for non-metro city."""
    calc = TaxCalculator(user_age=30)
    income = {
        'salary': Decimal('1000000'),
        'basic_salary': Decimal('500000'),
        'hra_received': Decimal('300000')
    }
    deductions = {
        'rent_paid_annual': Decimal('400000'),
        'city': 'Jaipur'
    }
    hra = calc._calculate_hra_exemption(income, deductions)
    
    # min(30L, 40L-50K, 40% of 5L) = min(30L, 35L, 2L) = 2L
    assert hra == Decimal('200000')


def test_80d_health_insurance():
    """Section 80D health insurance deduction."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1000000')}
    deductions = {
        'health_insurance_self': Decimal('25000'),
        'health_insurance_parents': Decimal('30000'),
        'parents_are_senior_citizens': True
    }
    result = calc._calculate_old_regime(income, deductions)
    
    # 80D: 25K (self, at limit) + 30K (senior parents, within 50K limit) = 55K
    # Total: 50K std + 55K 80D = 105K
    assert result['total_deductions'] == Decimal('105000')


def test_home_loan_interest_self_occupied():
    """Section 24(b) home loan interest for self-occupied property."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1000000')}
    deductions = {
        'home_loan_interest': Decimal('250000'),
        'property_is_self_occupied': True
    }
    result = calc._calculate_old_regime(income, deductions)
    
    # Should be capped at 2L for self-occupied
    # 50K std + 200K home loan = 250K
    assert result['total_deductions'] == Decimal('250000')


def test_home_loan_interest_let_out():
    """Section 24(b) home loan interest for let-out property (no cap)."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1000000')}
    deductions = {
        'home_loan_interest': Decimal('250000'),
        'property_is_self_occupied': False
    }
    result = calc._calculate_old_regime(income, deductions)
    
    # No cap for let-out property
    # 50K std + 250K home loan = 300K
    assert result['total_deductions'] == Decimal('300000')


def test_multiple_income_sources():
    """Calculate tax with multiple income sources."""
    calc = TaxCalculator(user_age=30)
    income = {
        'salary': Decimal('800000'),
        'rental': Decimal('120000'),
        'interest': Decimal('50000'),
        'dividend': Decimal('30000')
    }
    result = calc._calculate_new_regime(income)
    
    # Total income: 10L
    gross = Decimal('800000') + Decimal('120000') + Decimal('50000') + Decimal('30000')
    assert result['gross_income'] == gross


def test_calculate_tax_recommends_better_regime():
    """Test that calculate_tax recommends the regime with lower tax."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1000000')}
    deductions = {
        'epf_employee': Decimal('150000'),
        'ppf': Decimal('0')
    }
    
    result = calc.calculate_tax(income, deductions)
    
    assert 'old_regime' in result
    assert 'new_regime' in result
    assert 'recommended' in result
    assert 'savings' in result
    assert result['recommended'] in ['old', 'new']
    assert result['savings'] >= Decimal('0')


def test_high_income_new_regime_better():
    """High income with no deductions → new regime should be better."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('2000000')}
    deductions = {}
    
    result = calc.calculate_tax(income, deductions)
    
    # With high income and no deductions, new regime is typically better
    assert result['recommended'] == 'new'


def test_high_deductions_old_regime_better():
    """High deductions → In FY 2026-27, new regime is still better for most cases."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1500000')}
    deductions = {
        'epf_employee': Decimal('150000'),
        'health_insurance_self': Decimal('25000'),
        'home_loan_interest': Decimal('200000')
    }
    
    result = calc.calculate_tax(income, deductions)
    
    # Even with ₹3.75L deductions, new regime is better in FY 2026-27
    # New regime tax: ~₹97.5K vs Old regime: ~₹140.4K
    assert result['recommended'] == 'new'
    assert result['savings'] > Decimal('40000')  # Significant savings with new regime


def test_zero_income():
    """Test with zero income."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('0')}
    deductions = {}
    
    result = calc._calculate_new_regime(income)
    
    assert result['gross_income'] == Decimal('0')
    assert result['taxable_income'] == Decimal('0')
    assert result['total_tax'] == Decimal('0')


def test_donations_80g():
    """Test Section 80G donations deduction."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1000000')}
    deductions = {
        'donations_100_percent': Decimal('20000'),
        'donations_50_percent': Decimal('10000')
    }
    result = calc._calculate_old_regime(income, deductions)
    
    # 50K std + 20K (100%) + 5K (50% of 10K) = 75K
    assert result['total_deductions'] == Decimal('75000')


def test_education_loan_80e():
    """Test Section 80E education loan interest (no limit)."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1000000')}
    deductions = {
        'education_loan_interest': Decimal('300000')  # No cap
    }
    result = calc._calculate_old_regime(income, deductions)
    
    # 50K std + 300K education loan = 350K
    assert result['total_deductions'] == Decimal('350000')


def test_80tta_savings_interest_regular():
    """Test Section 80TTA savings interest for regular citizen."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1000000')}
    deductions = {
        'savings_interest_claimed': Decimal('15000')
    }
    result = calc._calculate_old_regime(income, deductions)
    
    # 50K std + min(15K, 10K limit) = 60K
    assert result['total_deductions'] == Decimal('60000')


def test_80ttb_savings_interest_senior():
    """Test Section 80TTB savings interest for senior citizen."""
    calc = TaxCalculator(user_age=65)
    income = {'salary': Decimal('1000000')}
    deductions = {
        'savings_interest_claimed': Decimal('60000')
    }
    result = calc._calculate_old_regime(income, deductions)
    
    # 50K std + min(60K, 50K limit for senior) = 100K
    assert result['total_deductions'] == Decimal('100000')


def test_nps_additional_80ccd1b():
    """Test Section 80CCD(1B) additional NPS deduction."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1000000')}
    deductions = {
        'epf_employee': Decimal('150000'),  # 80C
        'nps_additional': Decimal('50000')  # 80CCD(1B)
    }
    result = calc._calculate_old_regime(income, deductions)
    
    # 50K std + 150K (80C) + 50K (80CCD1B) = 250K
    assert result['total_deductions'] == Decimal('250000')


def test_hra_no_rent_paid():
    """HRA exemption when no rent is paid."""
    calc = TaxCalculator(user_age=30)
    income = {
        'salary': Decimal('1000000'),
        'basic_salary': Decimal('500000'),
        'hra_received': Decimal('300000')
    }
    deductions = {
        'rent_paid_annual': Decimal('0'),
        'city': 'Mumbai'
    }
    hra = calc._calculate_hra_exemption(income, deductions)
    
    # No rent paid → no HRA exemption
    assert hra == Decimal('0')


def test_preventive_checkup_80d():
    """Test preventive health checkup included in 80D."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1000000')}
    deductions = {
        'health_insurance_self': Decimal('20000'),
        'preventive_checkup': Decimal('5000')
    }
    result = calc._calculate_old_regime(income, deductions)
    
    # 50K std + min(20K + 5K, 25K limit) = 75K
    assert result['total_deductions'] == Decimal('75000')
