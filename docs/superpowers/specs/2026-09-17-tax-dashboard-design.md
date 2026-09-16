# Tax Projection Dashboard Design

**Date:** 2026-09-17  
**Priority:** P0 (Critical)  
**Score:** 19/20  
**Status:** Design Approved

---

## Overview

Real-time tax projection dashboard with dual-regime calculation (Old vs New), what-if planning mode, and smart refresh. Solves the biggest gap in Indian fintech: users don't know their tax liability until March 31, then panic-invest. This dashboard shows live projections throughout the year and recommends optimal tax regime.

### User Value

- **Real-time tracking:** YTD income, deductions, tax liability (updated after every relevant transaction)
- **Regime recommendation:** Auto-calculate both old & new regimes, recommend cheaper option with savings amount
- **What-if planning:** Interactive calculator to test scenarios ("If I invest ₹50K more in ELSS, how much tax do I save?")
- **Actionable insights:** "You can save ₹20K tax by investing ₹50K more in 80C before March 31"

### Scope

**In Scope:**
- Both tax regimes (Old + New) with FY 2026-27 rules
- 8 deduction sections: 80C, 80CCD(1B), 80D, 80E, 80G, 80TTA/TTB, 24(b), HRA
- Dashboard mode (passive tracking) + Planning mode (what-if calculator)
- Auto-detect income from transactions (salary, interest, dividends)
- Event-driven refresh (recalculate only when tax-relevant data changes)
- Accurate tax slabs, standard deduction, Section 87A rebate, 4% cess

**Out of Scope (Phase 2):**
- TDS auto-import from 26AS (manual entry only for MVP)
- Advance tax payment reminders
- Form 16 upload/parsing
- ITR filing integration (Cleartax API)
- Tier 3 deductions (80U, 80DD, 80DDB - rare cases)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────┐
│         Securo Backend (User's Server)          │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │  Tax Engine Module                       │  │
│  │  backend/app/tax/                        │  │
│  │                                          │  │
│  │  ┌────────────────────────────────────┐ │  │
│  │  │  Tax Calculator (engine.py)        │ │  │
│  │  │  - calculate_old_regime()          │ │  │
│  │  │  - calculate_new_regime()          │ │  │
│  │  │  - recommend_regime()              │ │  │
│  │  │  - apply_slabs()                   │ │  │
│  │  │  - calculate_hra_exemption()       │ │  │
│  │  └────────────────────────────────────┘ │  │
│  │                                          │  │
│  │  ┌────────────────────────────────────┐ │  │
│  │  │  Tax Service (services/tax.py)     │ │  │
│  │  │  - get_projection()                │ │  │
│  │  │  - recalculate_projection()        │ │  │
│  │  │  - auto_detect_income()            │ │  │
│  │  │  - save_income_sources()           │ │  │
│  │  │  - save_deductions()               │ │  │
│  │  └────────────────────────────────────┘ │  │
│  │                                          │  │
│  │  ┌────────────────────────────────────┐ │  │
│  │  │  Event Listeners (events.py)       │ │  │
│  │  │  - on_transaction_created()        │ │  │
│  │  │  - on_investment_marked_tax()      │ │  │
│  │  │  → mark projection as stale        │ │  │
│  │  └────────────────────────────────────┘ │  │
│  │                                          │  │
│  │  ┌────────────────────────────────────┐ │  │
│  │  │  Constants (constants.py)          │ │  │
│  │  │  - Tax slabs (old/new/senior)      │ │  │
│  │  │  - Deduction limits (80C, 80D...)  │ │  │
│  │  │  - Section 87A rebate rules        │ │  │
│  │  │  - Standard deduction (₹50K/₹75K)  │ │  │
│  │  └────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │  PostgreSQL Database                     │  │
│  │  - tax_income_sources                    │  │
│  │  - tax_deductions                        │  │
│  │  - tax_projections (cached results)      │  │
│  │  - tax_events_log                        │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │  FastAPI Endpoints                       │  │
│  │  GET  /api/tax/projection                │  │
│  │  GET  /api/tax/what-if                   │  │
│  │  POST /api/tax/income-sources            │  │
│  │  GET  /api/tax/income-sources/:fy        │  │
│  │  POST /api/tax/deductions                │  │
│  │  GET  /api/tax/deductions/:fy            │  │
│  │  POST /api/tax/auto-detect               │  │
│  │  POST /api/tax/recalculate               │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│   Frontend      │  Dashboard: YTD tax projection
│   (React)       │  Planning: What-if calculator
└─────────────────┘  Settings: Income/deduction entry
```

**Key Design Decisions:**

1. **Standalone tax module** — isolated from transactions/reports, clean separation
2. **Dual regime calculation** — Always calculate both, recommend cheaper option
3. **Event-driven refresh** — Recalculate only when income/deductions change (not every transaction)
4. **Cached projections** — Store results in DB, avoid expensive recalculation on every page load
5. **Hybrid income detection** — Auto-detect from transactions + manual override for accuracy
6. **Pure calculation engine** — Tax logic in pure functions (no DB access) for easy testing

---

## Data Model

### Tax Constants (FY 2026-27)

```python
# backend/app/tax/constants.py

CURRENT_FY = "2026-27"

# NEW TAX REGIME (Default)
NEW_REGIME_SLABS = [
    (0, 400000, 0),           # Up to ₹4L: 0%
    (400000, 800000, 0.05),   # ₹4L-8L: 5%
    (800000, 1200000, 0.10),  # ₹8L-12L: 10%
    (1200000, 1600000, 0.15), # ₹12L-16L: 15%
    (1600000, 2000000, 0.20), # ₹16L-20L: 20%
    (2000000, 2400000, 0.25), # ₹20L-24L: 25%
    (2400000, float('inf'), 0.30) # Above ₹24L: 30%
]

# OLD TAX REGIME
OLD_REGIME_SLABS = [
    (0, 250000, 0),           # Up to ₹2.5L: 0%
    (250000, 500000, 0.05),   # ₹2.5L-5L: 5%
    (500000, 1000000, 0.20),  # ₹5L-10L: 20%
    (1000000, float('inf'), 0.30) # Above ₹10L: 30%
]

# SENIOR CITIZEN (60-79 years, Old Regime Only)
SENIOR_CITIZEN_SLABS = [
    (0, 300000, 0),           # Up to ₹3L: 0%
    (300000, 500000, 0.05),
    (500000, 1000000, 0.20),
    (1000000, float('inf'), 0.30)
]

# SUPER SENIOR CITIZEN (80+ years, Old Regime Only)
SUPER_SENIOR_CITIZEN_SLABS = [
    (0, 500000, 0),           # Up to ₹5L: 0%
    (500000, 1000000, 0.20),
    (1000000, float('inf'), 0.30)
]

# STANDARD DEDUCTION
STANDARD_DEDUCTION_NEW_REGIME = 75000  # ₹75K
STANDARD_DEDUCTION_OLD_REGIME = 50000  # ₹50K

# SECTION 87A REBATE
SECTION_87A_REBATE_NEW = 60000         # Up to ₹60K rebate (new regime)
SECTION_87A_INCOME_LIMIT_NEW = 1200000 # If income ≤ ₹12L, tax can be 0

SECTION_87A_REBATE_OLD = 12500         # Up to ₹12.5K rebate (old regime)
SECTION_87A_INCOME_LIMIT_OLD = 500000  # If income ≤ ₹5L

# CESS
CESS_RATE = 0.04  # 4% on tax

# DEDUCTION LIMITS (Old Regime Only)
SECTION_80C_LIMIT = 150000            # ₹1.5L total
SECTION_80CCD_1B_LIMIT = 50000        # ₹50K additional NPS
SECTION_80D_SELF_LIMIT = 25000        # ₹25K health insurance (self)
SECTION_80D_PARENTS_LIMIT = 25000     # ₹25K parents (non-senior)
SECTION_80D_SENIOR_LIMIT = 50000      # ₹50K parents (senior citizen)
SECTION_80D_PREVENTIVE_LIMIT = 5000   # ₹5K preventive checkup (within 80D)
SECTION_24B_LIMIT = 200000            # ₹2L home loan interest (self-occupied)
SECTION_80TTA_LIMIT = 10000           # ₹10K savings interest (non-senior)
SECTION_80TTB_LIMIT = 50000           # ₹50K savings interest (senior)

# HRA EXEMPTION
HRA_METRO_PERCENT = 0.50              # 50% for metro cities
HRA_NON_METRO_PERCENT = 0.40          # 40% for non-metro
METRO_CITIES = ["Mumbai", "Delhi", "Kolkata", "Chennai", 
                "Bangalore", "Pune", "Hyderabad", "Ahmedabad"]

# AGE CATEGORIES
SENIOR_CITIZEN_AGE = 60
SUPER_SENIOR_CITIZEN_AGE = 80
```

---

### Database Tables

#### 1. Tax Income Sources

```sql
CREATE TABLE tax_income_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  financial_year VARCHAR(10) NOT NULL,  -- "2026-27"
  
  -- Income types (annual amounts)
  salary_annual DECIMAL(12, 2) DEFAULT 0,
  rental_income DECIMAL(12, 2) DEFAULT 0,
  interest_income DECIMAL(12, 2) DEFAULT 0,
  dividend_income DECIMAL(12, 2) DEFAULT 0,
  capital_gains_short_term DECIMAL(12, 2) DEFAULT 0,
  capital_gains_long_term DECIMAL(12, 2) DEFAULT 0,
  business_income DECIMAL(12, 2) DEFAULT 0,
  other_income DECIMAL(12, 2) DEFAULT 0,
  
  -- Salary breakdown (for HRA calculation)
  basic_salary DECIMAL(12, 2),
  hra_received DECIMAL(12, 2),
  special_allowance DECIMAL(12, 2),
  
  -- Auto-detection metadata
  salary_auto_detected BOOLEAN DEFAULT false,
  interest_auto_detected BOOLEAN DEFAULT false,
  last_auto_detection_at TIMESTAMP WITH TIME ZONE,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  UNIQUE(user_id, financial_year)
);

CREATE INDEX idx_tax_income_user_fy ON tax_income_sources(user_id, financial_year);
```

---

#### 2. Tax Deductions

```sql
CREATE TABLE tax_deductions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  financial_year VARCHAR(10) NOT NULL,
  
  -- Section 80C (₹1.5L combined limit)
  epf_employee DECIMAL(12, 2) DEFAULT 0,
  ppf DECIMAL(12, 2) DEFAULT 0,
  elss DECIMAL(12, 2) DEFAULT 0,
  lic_premium DECIMAL(12, 2) DEFAULT 0,
  nsc DECIMAL(12, 2) DEFAULT 0,
  tuition_fees DECIMAL(12, 2) DEFAULT 0,
  principal_repayment_home_loan DECIMAL(12, 2) DEFAULT 0,
  other_80c DECIMAL(12, 2) DEFAULT 0,
  
  -- Section 80CCD(1B) (₹50K additional NPS)
  nps_additional DECIMAL(12, 2) DEFAULT 0,
  
  -- Section 80D (Health insurance)
  health_insurance_self DECIMAL(12, 2) DEFAULT 0,      -- ₹25K limit
  health_insurance_parents DECIMAL(12, 2) DEFAULT 0,   -- ₹25K or ₹50K if senior
  parents_are_senior_citizens BOOLEAN DEFAULT false,
  preventive_checkup DECIMAL(12, 2) DEFAULT 0,         -- ₹5K within 80D
  
  -- Section 80E (Education loan interest, no limit)
  education_loan_interest DECIMAL(12, 2) DEFAULT 0,
  
  -- Section 80G (Donations)
  donations_100_percent DECIMAL(12, 2) DEFAULT 0,      -- 100% deductible
  donations_50_percent DECIMAL(12, 2) DEFAULT 0,       -- 50% deductible
  
  -- Section 80TTA/TTB (Savings interest)
  savings_interest_claimed DECIMAL(12, 2) DEFAULT 0,   -- ₹10K or ₹50K if senior
  
  -- Section 24(b) (Home loan interest)
  home_loan_interest DECIMAL(12, 2) DEFAULT 0,         -- ₹2L limit if self-occupied
  property_is_self_occupied BOOLEAN DEFAULT true,
  
  -- HRA calculation
  rent_paid_annual DECIMAL(12, 2) DEFAULT 0,
  city TEXT,                                            -- For metro check
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  UNIQUE(user_id, financial_year)
);

CREATE INDEX idx_tax_deductions_user_fy ON tax_deductions(user_id, financial_year);
```

---

#### 3. Tax Projections (Cached Results)

```sql
CREATE TABLE tax_projections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  financial_year VARCHAR(10) NOT NULL,
  
  -- Old Regime Results
  old_regime_gross_income DECIMAL(12, 2),
  old_regime_total_deductions DECIMAL(12, 2),
  old_regime_taxable_income DECIMAL(12, 2),
  old_regime_tax_liability DECIMAL(12, 2),
  old_regime_cess DECIMAL(12, 2),
  old_regime_total_tax DECIMAL(12, 2),
  
  -- New Regime Results
  new_regime_gross_income DECIMAL(12, 2),
  new_regime_taxable_income DECIMAL(12, 2),
  new_regime_tax_liability DECIMAL(12, 2),
  new_regime_cess DECIMAL(12, 2),
  new_regime_total_tax DECIMAL(12, 2),
  
  -- Recommendation
  recommended_regime VARCHAR(10),        -- 'old' or 'new'
  savings_with_recommendation DECIMAL(12, 2),
  
  -- TDS / Advance Tax Tracking (manual entry)
  tds_deducted DECIMAL(12, 2) DEFAULT 0,
  advance_tax_paid DECIMAL(12, 2) DEFAULT 0,
  tax_due_or_refund DECIMAL(12, 2),     -- Positive = due, Negative = refund
  
  -- Cache metadata
  calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_stale BOOLEAN DEFAULT false,       -- Set true when income/deductions change
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  UNIQUE(user_id, financial_year)
);

CREATE INDEX idx_tax_projections_user_fy ON tax_projections(user_id, financial_year);
CREATE INDEX idx_tax_projections_stale ON tax_projections(user_id, is_stale) WHERE is_stale = true;
```

---

#### 4. Tax Events Log (Debugging)

```sql
CREATE TABLE tax_events_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  financial_year VARCHAR(10) NOT NULL,
  
  event_type VARCHAR(50) NOT NULL,      -- 'income_changed', 'deduction_added', 'transaction_created', etc.
  event_data JSONB,                     -- Additional context
  triggered_recalculation BOOLEAN DEFAULT true,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tax_events_user ON tax_events_log(user_id, created_at DESC);
```

---

## Tax Calculation Engine

**Core calculation logic (pure functions, no DB access):**

```python
# backend/app/tax/engine.py

from decimal import Decimal
from typing import Dict
from .constants import *

class TaxCalculator:
    """
    Pure tax calculation engine.
    Inputs: income dict, deductions dict, user age
    Output: Tax liability in both regimes + recommendation
    """
    
    def __init__(self, user_age: int, financial_year: str = CURRENT_FY):
        self.user_age = user_age
        self.financial_year = financial_year
        self.is_senior = user_age >= SENIOR_CITIZEN_AGE
        self.is_super_senior = user_age >= SUPER_SENIOR_CITIZEN_AGE
    
    def calculate_tax(
        self, 
        income: Dict[str, Decimal],
        deductions: Dict[str, Decimal]
    ) -> Dict:
        """
        Calculate tax in both regimes, recommend cheaper option.
        
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
    
    def _calculate_old_regime(self, income: Dict, deductions: Dict) -> Dict:
        """
        Old regime: Allows all deductions, lower basic exemption.
        """
        
        # Step 1: Gross income
        gross_income = self._sum_all_income(income)
        
        # Step 2: Calculate deductions (with limits)
        total_deductions = self._calculate_deductions_old(income, deductions)
        
        # Step 3: Taxable income
        taxable_income = max(Decimal(0), gross_income - total_deductions)
        
        # Step 4: Apply slabs
        if self.is_super_senior:
            slabs = SUPER_SENIOR_CITIZEN_SLABS
        elif self.is_senior:
            slabs = SENIOR_CITIZEN_SLABS
        else:
            slabs = OLD_REGIME_SLABS
        
        tax_liability = self._apply_slabs(taxable_income, slabs)
        
        # Step 5: Section 87A rebate (income ≤ ₹5L → tax can be 0)
        if taxable_income <= SECTION_87A_INCOME_LIMIT_OLD:
            rebate = min(tax_liability, Decimal(SECTION_87A_REBATE_OLD))
            tax_liability -= rebate
        
        # Step 6: Add 4% cess
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
    
    def _calculate_new_regime(self, income: Dict) -> Dict:
        """
        New regime: Higher basic exemption (₹4L), no deductions except standard (₹75K).
        """
        
        gross_income = self._sum_all_income(income)
        
        # Only standard deduction
        total_deductions = Decimal(STANDARD_DEDUCTION_NEW_REGIME)
        
        taxable_income = max(Decimal(0), gross_income - total_deductions)
        
        # Apply new slabs
        tax_liability = self._apply_slabs(taxable_income, NEW_REGIME_SLABS)
        
        # Section 87A rebate (income ≤ ₹12L → tax can be 0, rebate up to ₹60K)
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
    
    def _calculate_deductions_old(self, income: Dict, deductions: Dict) -> Decimal:
        """
        Calculate all deductions for old regime (with limits).
        """
        
        total = Decimal(0)
        
        # 1. Standard deduction (₹50K)
        total += Decimal(STANDARD_DEDUCTION_OLD_REGIME)
        
        # 2. Section 80C (max ₹1.5L)
        sec_80c = sum([
            deductions.get('epf_employee', Decimal(0)),
            deductions.get('ppf', Decimal(0)),
            deductions.get('elss', Decimal(0)),
            deductions.get('lic_premium', Decimal(0)),
            deductions.get('nsc', Decimal(0)),
            deductions.get('tuition_fees', Decimal(0)),
            deductions.get('principal_repayment', Decimal(0)),
            deductions.get('other_80c', Decimal(0))
        ])
        total += min(sec_80c, Decimal(SECTION_80C_LIMIT))
        
        # 3. Section 80CCD(1B) - Additional NPS (max ₹50K)
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
            total += home_int  # No limit if let-out
        
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
        option_2 = rent_paid - (basic * Decimal(0.1))
        is_metro = city in METRO_CITIES
        metro_pct = HRA_METRO_PERCENT if is_metro else HRA_NON_METRO_PERCENT
        option_3 = basic * Decimal(metro_pct)
        
        hra_exemption = min(option_1, option_2, option_3)
        return max(Decimal(0), hra_exemption)
    
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
    
    def _apply_slabs(self, taxable_income: Decimal, slabs: list) -> Decimal:
        """Apply progressive tax slabs."""
        tax = Decimal(0)
        
        for lower, upper, rate in slabs:
            if taxable_income <= lower:
                break
            taxable_in_slab = min(taxable_income, Decimal(upper)) - Decimal(lower)
            tax += taxable_in_slab * Decimal(rate)
        
        return tax
```

---

## Backend API

```python
# backend/app/api/tax.py

@router.get("/projection")
async def get_tax_projection(
    financial_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get cached projection, recalculate if stale."""
    fy = financial_year or CURRENT_FY
    projection = await tax_service.get_projection(db, current_user.id, fy, recalculate_if_stale=True)
    if not projection:
        raise HTTPException(404, "No tax data found")
    return projection

@router.get("/what-if")
async def calculate_what_if(
    income: TaxIncomeWhatIf,
    deductions: TaxDeductionsWhatIf,
    current_user: User = Depends(get_current_user)
):
    """Calculate tax with hypothetical values (not saved)."""
    result = tax_service.calculate_what_if(current_user.age, income, deductions)
    return result

@router.post("/income-sources")
async def save_income_sources(...):
    """Save income, trigger recalculation."""
    income_source = await tax_service.save_income_sources(...)
    return income_source

@router.post("/deductions")
async def save_deductions(...):
    """Save deductions, trigger recalculation."""
    deduction = await tax_service.save_deductions(...)
    return deduction

@router.post("/auto-detect")
async def auto_detect_income(...):
    """Auto-detect income from transactions."""
    detected = await tax_service.auto_detect_income(...)
    return {"detected": detected, "message": "Review and confirm"}

@router.post("/recalculate")
async def force_recalculate(...):
    """Manual refresh button."""
    projection = await tax_service.recalculate_projection(...)
    return {"projection": projection}
```

---

## Event Listeners (Smart Refresh)

```python
# backend/app/tax/events.py

async def on_transaction_created(db: AsyncSession, transaction: Transaction):
    """
    Triggered after transaction created.
    Mark tax projection stale if it's income-related.
    """
    
    # Only large credits (potential salary)
    if transaction.type == 'credit' and transaction.amount > 25000:
        fy = _get_financial_year(transaction.transaction_date)
        await tax_service._mark_projection_stale(db, transaction.user_id, fy)
        await tax_service._log_event(db, transaction.user_id, fy, "income_transaction_added")

async def on_investment_marked_tax_saving(
    db: AsyncSession,
    user_id: UUID,
    investment_type: str,
    amount: Decimal,
    date: date
):
    """
    Triggered when user marks investment as tax-saving (80C, etc.)
    From EPF/PPF/MF features.
    """
    fy = _get_financial_year(date)
    await tax_service._mark_projection_stale(db, user_id, fy)
    await tax_service._log_event(db, user_id, fy, "tax_saving_investment_added", {"type": investment_type})
```

---

## Frontend UI

### Dashboard View

```typescript
// frontend/src/pages/tax-dashboard.tsx

export default function TaxDashboardPage() {
  const { data: projection } = useQuery(['tax-projection'], () => api.get('/api/tax/projection'))
  
  return (
    <div className="space-y-6">
      <PageHeader title="Tax Dashboard" />
      
      {/* Regime Comparison */}
      <RegimeComparisonCard projection={projection} />
      
      {/* Tabs: Dashboard vs Planning */}
      <Tabs defaultValue="dashboard">
        <TabsList>
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="planning">What-If Planning</TabsTrigger>
        </TabsList>
        
        <TabsContent value="dashboard">
          <DashboardView projection={projection} />
        </TabsContent>
        
        <TabsContent value="planning">
          <PlanningView />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function RegimeComparisonCard({ projection }) {
  const recommended = projection.recommended_regime
  const savings = projection.savings_with_recommendation
  
  return (
    <Card className="p-6">
      <h3 className="font-semibold mb-4">Regime Recommendation</h3>
      
      <div className="grid grid-cols-2 gap-4">
        <div className={recommended === 'old' ? 'border-primary bg-primary/5' : ''}>
          <div className="text-sm text-muted-foreground">Old Regime</div>
          <div className="text-2xl font-bold">₹{formatNumber(projection.old_regime_total_tax)}</div>
          {recommended === 'old' && <Badge>Recommended</Badge>}
        </div>
        
        <div className={recommended === 'new' ? 'border-primary bg-primary/5' : ''}>
          <div className="text-sm text-muted-foreground">New Regime</div>
          <div className="text-2xl font-bold">₹{formatNumber(projection.new_regime_total_tax)}</div>
          {recommended === 'new' && <Badge>Recommended</Badge>}
        </div>
      </div>
      
      <Alert className="mt-4">
        <TrendingDown className="w-4 h-4" />
        <AlertTitle>Save ₹{formatNumber(savings)} with {recommended} regime</AlertTitle>
        <AlertDescription>
          {recommended === 'old' 
            ? 'Your tax-saving investments make old regime better.'
            : 'New regime is better. Consider maximizing 80C investments if you want to switch.'}
        </AlertDescription>
      </Alert>
    </Card>
  )
}

function DashboardView({ projection }) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <KPICard label="Gross Income" value={projection.old_regime_gross_income} />
      <KPICard label="Total Deductions" value={projection.old_regime_total_deductions} subtitle="80C + 80D + HRA" />
      <KPICard label="Tax Liability" value={projection.old_regime_total_tax} color="red" />
      
      {/* Deduction Breakdown, Payment Tracker, etc. */}
    </div>
  )
}

function PlanningView() {
  const [income, setIncome] = useState({})
  const [deductions, setDeductions] = useState({})
  
  const { data: whatIf } = useQuery(
    ['tax-what-if', income, deductions],
    () => api.get('/api/tax/what-if', { params: { income, deductions } }),
    { enabled: Object.keys(income).length > 0 }
  )
  
  return (
    <div className="grid grid-cols-2 gap-6">
      <div>
        <h4 className="font-semibold mb-4">Adjust Values</h4>
        <Input label="Salary" type="number" value={income.salary} onChange={...} />
        <Slider label="80C Investments" min={0} max={150000} value={deductions.total_80c} onChange={...} />
        {/* More sliders */}
      </div>
      
      <div>
        <h4 className="font-semibold mb-4">Projected Tax</h4>
        {whatIf && (
          <>
            <Card>Old Regime: ₹{whatIf.old_regime.total_tax}</Card>
            <Card>New Regime: ₹{whatIf.new_regime.total_tax}</Card>
          </>
        )}
      </div>
    </div>
  )
}
```

---

## Testing Strategy

**Unit Tests:**
- Tax calculator: 50+ scenarios (different incomes, ages, deductions)
- Test Section 87A rebate edge cases (exactly ₹5L, ₹12L income)
- Test 80C limit (₹2.3L input → capped at ₹1.5L)
- Test HRA calculation (metro vs non-metro)
- Test senior citizen slabs

**Integration Tests:**
- End-to-end: Save income → Save deductions → Get projection → Correct tax calculated
- Event-driven refresh: Create income transaction → Projection marked stale → Next API call recalculates
- What-if calculator: Change slider → Instant tax recalculation (no DB save)

**Accuracy Validation:**
- Compare with Cleartax/ET Money for same inputs
- Test against 20 real user scenarios (anonymized Form 16 data)

---

## Migration & Rollout

**Week 1-2: Backend Core**
- Database migrations (4 new tables)
- Tax engine implementation (engine.py, constants.py)
- Tax service (business logic)
- Unit tests (50+ test cases)

**Week 3: API & Events**
- FastAPI endpoints (8 endpoints)
- Event listeners (transaction created, etc.)
- Integration tests

**Week 4: Frontend**
- Dashboard page (regime comparison, KPI cards)
- Planning mode (what-if calculator)
- Settings (income/deduction entry)
- Auto-detect income UI

**Week 5: Testing & Polish**
- User acceptance testing (10 beta users)
- Bug fixes
- Documentation (user guide, tax rules explanation)

**Week 6: Launch**
- Feature flag rollout (10% → 50% → 100%)
- Monitor accuracy (user corrections, support tickets)
- Blog post announcement

---

## Success Metrics

**Adoption:**
- 70% of users add income sources within 30 days
- 50% check tax dashboard monthly (Dec-Mar higher)

**Accuracy:**
- <5% user corrections to auto-detected income
- Tax calculation matches Cleartax within ₹100 (99% of cases)

**Engagement:**
- What-if calculator used by 30% of users in Dec-Feb (tax season)
- Average 3 sessions per user during tax season

**Business Impact:**
- User retention +15% (tax planning keeps users engaged)
- Feature mentioned in 5-star reviews
- NPS +10 points

---

## Future Enhancements (Phase 2)

1. **26AS Integration** (TDS auto-import from IT portal) - 3 weeks
2. **Form 16 Upload** (PDF parsing → auto-fill income) - 2 weeks
3. **Advance Tax Calculator** (quarterly payment reminders) - 2 weeks
4. **ITR Filing Integration** (Cleartax API → one-click filing) - 4 weeks
5. **Tax Optimizer** (ML suggests optimal 80C/80D allocation) - 4 weeks
6. **Historical Tax Comparison** (YoY tax trends) - 1 week
7. **Tier 3 Deductions** (80U, 80DD, 80DDB - rare cases) - 1 week

---

## Open Questions

1. **User date of birth:** Need DOB in users table for age calculation (senior citizen slabs). Add in migration?
   - **Decision:** Add `date_of_birth` column to users table (nullable, user can set in profile)

2. **Financial year selection:** Support multiple FYs or just current FY for MVP?
   - **Decision:** MVP supports current FY only, add FY selector in Phase 2

3. **TDS tracking:** Manual entry only or attempt to parse from 26AS?
   - **Decision:** Manual entry for MVP (26AS requires IT portal login → Phase 2)

4. **Capital gains source:** Wait for MF/stock portfolio feature (P0) or manual entry?
   - **Decision:** Manual entry for MVP, auto-populate after portfolio features launch

---

## Document Status

- ✅ Architecture defined
- ✅ Tax rules researched (FY 2026-27)
- ✅ Data model designed (4 tables)
- ✅ Calculation engine specified (both regimes)
- ✅ API endpoints designed (8 endpoints)
- ✅ Event listeners planned (smart refresh)
- ✅ Frontend UI outlined (dashboard + planning)
- ✅ Testing strategy ready

**Next Step:** User review → Writing implementation plan (writing-plans skill)

---

**End of Design Document**
