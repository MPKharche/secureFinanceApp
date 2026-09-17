# Tax Projection Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build real-time tax projection dashboard with dual-regime calculation (Old vs New), what-if planning, and smart refresh for Indian tax compliance.

**Architecture:** Standalone tax module with pure calculation engine, event-driven refresh triggers, cached projections in PostgreSQL, and React frontend with dashboard + planning modes.

**Tech Stack:** FastAPI (backend), PostgreSQL (data), SQLAlchemy (ORM), React + shadcn/ui (frontend), decimal.Decimal (precision), event listeners (refresh triggers)

## Global Constraints

- Python 3.10+ (backend)
- PostgreSQL 14+ (database)
- React 18+ (frontend)
- All monetary values: decimal.Decimal (no floats)
- Financial year format: "YYYY-YY" (e.g., "2026-27")
- Tax rules: FY 2026-27 (per spec constants)
- All amounts in INR (₹)
- User age required for senior citizen slabs
- Test coverage: >80% for tax engine

---

## Task 1: Database Schema & Migrations

**Files:**
- Create: `backend/app/alembic/versions/YYYYMMDD_add_tax_tables.py`
- Create: `backend/app/models/tax.py`
- Modify: `backend/app/models/__init__.py` (import tax models)
- Modify: `backend/app/models/user.py` (add date_of_birth field)

**Interfaces:**
- Consumes: Existing database connection, alembic setup
- Produces: 
  - `TaxIncomeSource` model with user_id, financial_year, salary_annual, rental_income, etc.
  - `TaxDeduction` model with user_id, financial_year, 80C fields, 80D fields, etc.
  - `TaxProjection` model with user_id, financial_year, old_regime_*, new_regime_*, recommended_regime
  - `TaxEventLog` model with user_id, event_type, event_data
  - `User.date_of_birth` field (Date, nullable)

- [ ] **Step 1: Write the failing migration test**

```python
# tests/test_migrations/test_tax_tables.py
import pytest
from sqlalchemy import inspect
from app.database import engine

def test_tax_tables_exist():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    assert 'tax_income_sources' in tables
    assert 'tax_deductions' in tables
    assert 'tax_projections' in tables
    assert 'tax_events_log' in tables

def test_user_dob_column_exists():
    inspector = inspect(engine)
    columns = {col['name'] for col in inspector.get_columns('users')}
    assert 'date_of_birth' in columns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_migrations/test_tax_tables.py -v`
Expected: FAIL with "table does not exist" or "column not found"

- [ ] **Step 3: Create SQLAlchemy models**

```python
# backend/app/models/tax.py
from sqlalchemy import Column, String, DECIMAL, Boolean, TIMESTAMP, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class TaxIncomeSource(Base):
    __tablename__ = 'tax_income_sources'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False)
    financial_year = Column(String(10), nullable=False)
    
    # Income types
    salary_annual = Column(DECIMAL(12, 2), default=0)
    rental_income = Column(DECIMAL(12, 2), default=0)
    interest_income = Column(DECIMAL(12, 2), default=0)
    dividend_income = Column(DECIMAL(12, 2), default=0)
    capital_gains_short_term = Column(DECIMAL(12, 2), default=0)
    capital_gains_long_term = Column(DECIMAL(12, 2), default=0)
    business_income = Column(DECIMAL(12, 2), default=0)
    other_income = Column(DECIMAL(12, 2), default=0)
    
    # Salary breakdown for HRA
    basic_salary = Column(DECIMAL(12, 2))
    hra_received = Column(DECIMAL(12, 2))
    special_allowance = Column(DECIMAL(12, 2))
    
    # Auto-detection
    salary_auto_detected = Column(Boolean, default=False)
    interest_auto_detected = Column(Boolean, default=False)
    last_auto_detection_at = Column(TIMESTAMP(timezone=True))
    
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="tax_income_sources")

class TaxDeduction(Base):
    __tablename__ = 'tax_deductions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False)
    financial_year = Column(String(10), nullable=False)
    
    # Section 80C
    epf_employee = Column(DECIMAL(12, 2), default=0)
    ppf = Column(DECIMAL(12, 2), default=0)
    elss = Column(DECIMAL(12, 2), default=0)
    lic_premium = Column(DECIMAL(12, 2), default=0)
    nsc = Column(DECIMAL(12, 2), default=0)
    tuition_fees = Column(DECIMAL(12, 2), default=0)
    principal_repayment_home_loan = Column(DECIMAL(12, 2), default=0)
    other_80c = Column(DECIMAL(12, 2), default=0)
    
    # Section 80CCD(1B)
    nps_additional = Column(DECIMAL(12, 2), default=0)
    
    # Section 80D
    health_insurance_self = Column(DECIMAL(12, 2), default=0)
    health_insurance_parents = Column(DECIMAL(12, 2), default=0)
    parents_are_senior_citizens = Column(Boolean, default=False)
    preventive_checkup = Column(DECIMAL(12, 2), default=0)
    
    # Section 80E
    education_loan_interest = Column(DECIMAL(12, 2), default=0)
    
    # Section 80G
    donations_100_percent = Column(DECIMAL(12, 2), default=0)
    donations_50_percent = Column(DECIMAL(12, 2), default=0)
    
    # Section 80TTA/TTB
    savings_interest_claimed = Column(DECIMAL(12, 2), default=0)
    
    # Section 24(b)
    home_loan_interest = Column(DECIMAL(12, 2), default=0)
    property_is_self_occupied = Column(Boolean, default=True)
    
    # HRA
    rent_paid_annual = Column(DECIMAL(12, 2), default=0)
    city = Column(String)
    
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="tax_deductions")

class TaxProjection(Base):
    __tablename__ = 'tax_projections'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False)
    financial_year = Column(String(10), nullable=False)
    
    # Old regime results
    old_regime_gross_income = Column(DECIMAL(12, 2))
    old_regime_total_deductions = Column(DECIMAL(12, 2))
    old_regime_taxable_income = Column(DECIMAL(12, 2))
    old_regime_tax_liability = Column(DECIMAL(12, 2))
    old_regime_cess = Column(DECIMAL(12, 2))
    old_regime_total_tax = Column(DECIMAL(12, 2))
    
    # New regime results
    new_regime_gross_income = Column(DECIMAL(12, 2))
    new_regime_taxable_income = Column(DECIMAL(12, 2))
    new_regime_tax_liability = Column(DECIMAL(12, 2))
    new_regime_cess = Column(DECIMAL(12, 2))
    new_regime_total_tax = Column(DECIMAL(12, 2))
    
    # Recommendation
    recommended_regime = Column(String(10))
    savings_with_recommendation = Column(DECIMAL(12, 2))
    
    # TDS tracking
    tds_deducted = Column(DECIMAL(12, 2), default=0)
    advance_tax_paid = Column(DECIMAL(12, 2), default=0)
    tax_due_or_refund = Column(DECIMAL(12, 2))
    
    # Cache metadata
    calculated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    is_stale = Column(Boolean, default=False)
    
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="tax_projections")

class TaxEventLog(Base):
    __tablename__ = 'tax_events_log'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    financial_year = Column(String(10), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_data = Column(JSONB)
    triggered_recalculation = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
```

- [ ] **Step 4: Add date_of_birth to User model**

```python
# backend/app/models/user.py
# Add this field to the User class:
date_of_birth = Column(Date, nullable=True)

# Add relationships:
tax_income_sources = relationship("TaxIncomeSource", back_populates="user", cascade="all, delete-orphan")
tax_deductions = relationship("TaxDeduction", back_populates="user", cascade="all, delete-orphan")
tax_projections = relationship("TaxProjection", back_populates="user", cascade="all, delete-orphan")
```

- [ ] **Step 5: Create alembic migration**

```python
# backend/app/alembic/versions/YYYYMMDD_add_tax_tables.py
"""add tax tables and user dob

Revision ID: <generated>
Revises: <previous_revision>
Create Date: 2026-09-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '<generated>'
down_revision = '<previous_revision>'

def upgrade():
    # Add date_of_birth to users
    op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))
    
    # Create tax_income_sources
    op.create_table(
        'tax_income_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('financial_year', sa.String(10), nullable=False),
        sa.Column('salary_annual', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('rental_income', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('interest_income', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('dividend_income', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('capital_gains_short_term', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('capital_gains_long_term', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('business_income', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('other_income', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('basic_salary', sa.DECIMAL(12, 2)),
        sa.Column('hra_received', sa.DECIMAL(12, 2)),
        sa.Column('special_allowance', sa.DECIMAL(12, 2)),
        sa.Column('salary_auto_detected', sa.Boolean(), server_default='false'),
        sa.Column('interest_auto_detected', sa.Boolean(), server_default='false'),
        sa.Column('last_auto_detection_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'financial_year')
    )
    op.create_index('idx_tax_income_user_fy', 'tax_income_sources', ['user_id', 'financial_year'])
    
    # Create tax_deductions (similar structure)
    op.create_table('tax_deductions', ...)
    op.create_index('idx_tax_deductions_user_fy', 'tax_deductions', ['user_id', 'financial_year'])
    
    # Create tax_projections
    op.create_table('tax_projections', ...)
    op.create_index('idx_tax_projections_user_fy', 'tax_projections', ['user_id', 'financial_year'])
    op.create_index('idx_tax_projections_stale', 'tax_projections', ['user_id', 'is_stale'], postgresql_where=sa.text('is_stale = true'))
    
    # Create tax_events_log
    op.create_table('tax_events_log', ...)
    op.create_index('idx_tax_events_user', 'tax_events_log', ['user_id', sa.text('created_at DESC')])

def downgrade():
    op.drop_table('tax_events_log')
    op.drop_table('tax_projections')
    op.drop_table('tax_deductions')
    op.drop_table('tax_income_sources')
    op.drop_column('users', 'date_of_birth')
```

- [ ] **Step 6: Run migration**

Run: `alembic upgrade head`
Expected: SUCCESS with "Running upgrade... -> add_tax_tables"

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/test_migrations/test_tax_tables.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/tax.py backend/app/models/user.py backend/app/alembic/versions/ tests/test_migrations/test_tax_tables.py
git commit -m "feat(tax): add tax tables and user DOB field"
```

**Estimate:** 3 hours

---

## Task 2: Tax Constants Module

**Files:**
- Create: `backend/app/tax/__init__.py`
- Create: `backend/app/tax/constants.py`
- Create: `tests/tax/test_constants.py`

**Interfaces:**
- Consumes: None (pure data)
- Produces: 
  - `CURRENT_FY = "2026-27"`
  - `NEW_REGIME_SLABS` (list of tuples)
  - `OLD_REGIME_SLABS` (list of tuples)
  - `SENIOR_CITIZEN_SLABS`, `SUPER_SENIOR_CITIZEN_SLABS`
  - `STANDARD_DEDUCTION_NEW_REGIME = 75000`
  - `STANDARD_DEDUCTION_OLD_REGIME = 50000`
  - All deduction limits (80C, 80D, etc.)
  - `METRO_CITIES` list

- [ ] **Step 1: Write test for constants validation**

```python
# tests/tax/test_constants.py
import pytest
from app.tax.constants import *

def test_current_fy_format():
    assert CURRENT_FY == "2026-27"
    assert len(CURRENT_FY) == 7

def test_new_regime_slabs_structure():
    assert len(NEW_REGIME_SLABS) == 7
    # First slab: 0-4L at 0%
    assert NEW_REGIME_SLABS[0] == (0, 400000, 0)
    # Last slab: >24L at 30%
    assert NEW_REGIME_SLABS[-1][2] == 0.30

def test_old_regime_slabs_structure():
    assert len(OLD_REGIME_SLABS) == 4
    assert OLD_REGIME_SLABS[0] == (0, 250000, 0)
    assert OLD_REGIME_SLABS[-1][2] == 0.30

def test_deduction_limits():
    assert SECTION_80C_LIMIT == 150000
    assert SECTION_80CCD_1B_LIMIT == 50000
    assert SECTION_80D_SELF_LIMIT == 25000
    assert SECTION_24B_LIMIT == 200000

def test_metro_cities_list():
    assert "Mumbai" in METRO_CITIES
    assert "Delhi" in METRO_CITIES
    assert len(METRO_CITIES) == 8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tax/test_constants.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.tax'"

- [ ] **Step 3: Create constants module**

```python
# backend/app/tax/__init__.py
"""Tax calculation module for Indian income tax."""

# backend/app/tax/constants.py
"""Tax constants for FY 2026-27."""

CURRENT_FY = "2026-27"

# NEW TAX REGIME (Default)
NEW_REGIME_SLABS = [
    (0, 400000, 0),
    (400000, 800000, 0.05),
    (800000, 1200000, 0.10),
    (1200000, 1600000, 0.15),
    (1600000, 2000000, 0.20),
    (2000000, 2400000, 0.25),
    (2400000, float('inf'), 0.30)
]

# OLD TAX REGIME
OLD_REGIME_SLABS = [
    (0, 250000, 0),
    (250000, 500000, 0.05),
    (500000, 1000000, 0.20),
    (1000000, float('inf'), 0.30)
]

# SENIOR CITIZEN (60-79 years, Old Regime Only)
SENIOR_CITIZEN_SLABS = [
    (0, 300000, 0),
    (300000, 500000, 0.05),
    (500000, 1000000, 0.20),
    (1000000, float('inf'), 0.30)
]

# SUPER SENIOR CITIZEN (80+ years, Old Regime Only)
SUPER_SENIOR_CITIZEN_SLABS = [
    (0, 500000, 0),
    (500000, 1000000, 0.20),
    (1000000, float('inf'), 0.30)
]

# STANDARD DEDUCTION
STANDARD_DEDUCTION_NEW_REGIME = 75000
STANDARD_DEDUCTION_OLD_REGIME = 50000

# SECTION 87A REBATE
SECTION_87A_REBATE_NEW = 60000
SECTION_87A_INCOME_LIMIT_NEW = 1200000
SECTION_87A_REBATE_OLD = 12500
SECTION_87A_INCOME_LIMIT_OLD = 500000

# CESS
CESS_RATE = 0.04

# DEDUCTION LIMITS (Old Regime Only)
SECTION_80C_LIMIT = 150000
SECTION_80CCD_1B_LIMIT = 50000
SECTION_80D_SELF_LIMIT = 25000
SECTION_80D_PARENTS_LIMIT = 25000
SECTION_80D_SENIOR_LIMIT = 50000
SECTION_80D_PREVENTIVE_LIMIT = 5000
SECTION_24B_LIMIT = 200000
SECTION_80TTA_LIMIT = 10000
SECTION_80TTB_LIMIT = 50000

# HRA EXEMPTION
HRA_METRO_PERCENT = 0.50
HRA_NON_METRO_PERCENT = 0.40
METRO_CITIES = [
    "Mumbai", "Delhi", "Kolkata", "Chennai",
    "Bangalore", "Pune", "Hyderabad", "Ahmedabad"
]

# AGE CATEGORIES
SENIOR_CITIZEN_AGE = 60
SUPER_SENIOR_CITIZEN_AGE = 80
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/tax/test_constants.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/tax/ tests/tax/
git commit -m "feat(tax): add tax constants for FY 2026-27"
```

**Estimate:** 1 hour

---

## Task 3: Tax Calculator Engine (Core Logic)

**Files:**
- Create: `backend/app/tax/engine.py`
- Create: `tests/tax/test_engine.py`

**Interfaces:**
- Consumes: `tax.constants.*`, income dict, deductions dict, user_age (int)
- Produces: `TaxCalculator` class with methods:
  - `calculate_tax(income: Dict, deductions: Dict) -> Dict`
  - `_calculate_old_regime(income, deductions) -> Dict`
  - `_calculate_new_regime(income) -> Dict`
  - `_apply_slabs(taxable_income, slabs) -> Decimal`
  - `_calculate_hra_exemption(income, deductions) -> Decimal`

- [ ] **Step 1: Write failing tests for tax calculation**

```python
# tests/tax/test_engine.py
import pytest
from decimal import Decimal
from app.tax.engine import TaxCalculator

def test_new_regime_no_deductions():
    """Income ₹10L, new regime → Tax should be ₹52,000 (before rebate)."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1000000')}
    result = calc._calculate_new_regime(income)
    
    # 10L - 75K std deduction = 9.25L taxable
    # 0-4L: 0, 4-8L: 20K, 8-9.25L: 12.5K = 32.5K + cess
    assert result['taxable_income'] == Decimal('925000')
    assert result['tax_liability'] > 0

def test_old_regime_with_80c():
    """Income ₹8L, 80C ₹1.5L → Tax lower than new regime."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('800000')}
    deductions = {
        'epf_employee': Decimal('150000'),
        'rent_paid_annual': Decimal('0')
    }
    result = calc._calculate_old_regime(income, deductions)
    
    # 8L - 50K std - 1.5L 80C = 6.5L taxable
    assert result['total_deductions'] >= Decimal('200000')
    assert result['taxable_income'] <= Decimal('600000')

def test_section_87a_rebate_new_regime():
    """Income ₹7L in new regime → Section 87A rebate should apply."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('700000')}
    result = calc._calculate_new_regime(income)
    
    # Taxable: 7L - 75K = 6.25L (within ₹12L limit)
    # Tax before rebate: (4-6.25L)*5% = 11.25K
    # Rebate reduces it significantly
    assert result['tax_liability'] < Decimal('5000')

def test_senior_citizen_slabs():
    """65-year-old gets ₹3L basic exemption in old regime."""
    calc = TaxCalculator(user_age=65)
    income = {'salary': Decimal('350000')}
    deductions = {}
    result = calc._calculate_old_regime(income, deductions)
    
    # 3.5L - 50K std = 3L taxable (senior slab: 0-3L free)
    assert result['tax_liability'] == Decimal('0')

def test_80c_limit_capping():
    """80C investments of ₹2.3L should be capped at ₹1.5L."""
    calc = TaxCalculator(user_age=30)
    income = {'salary': Decimal('1000000')}
    deductions = {
        'epf_employee': Decimal('100000'),
        'ppf': Decimal('100000'),
        'elss': Decimal('1100000')  # Total 2.3L
    }
    result = calc._calculate_old_regime(income, deductions)
    
    # Should include only 1.5L from 80C
    assert result['total_deductions'] <= Decimal('200000')  # 50K std + 150K 80C

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tax/test_engine.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.tax.engine'"

- [ ] **Step 3: Implement TaxCalculator class (part 1: structure)**

```python
# backend/app/tax/engine.py
from decimal import Decimal
from typing import Dict, List, Tuple
from .constants import *

class TaxCalculator:
    """Pure tax calculation engine (no database access)."""
    
    def __init__(self, user_age: int, financial_year: str = CURRENT_FY):
        self.user_age = user_age
        self.financial_year = financial_year
        self.is_senior = user_age >= SENIOR_CITIZEN_AGE
        self.is_super_senior = user_age >= SUPER_SENIOR_CITIZEN_AGE
    
    def calculate_tax(self, income: Dict[str, Decimal], deductions: Dict[str, Decimal]) -> Dict:
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
```

- [ ] **Step 4: Implement new regime calculation**

```python
# Continue in backend/app/tax/engine.py

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
```

- [ ] **Step 5: Implement old regime calculation**

```python
# Continue in backend/app/tax/engine.py

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
```

- [ ] **Step 6: Implement deductions calculation**

```python
# Continue in backend/app/tax/engine.py

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
    
    # 5. Section 80E - Education loan interest
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
```

- [ ] **Step 7: Implement HRA exemption**

```python
# Continue in backend/app/tax/engine.py

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
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/tax/test_engine.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 9: Commit**

```bash
git add backend/app/tax/engine.py tests/tax/test_engine.py
git commit -m "feat(tax): implement tax calculator engine with dual-regime support"
```

**Estimate:** 6 hours

---

*[Plan continues with remaining tasks: Tax Service Layer, API Endpoints, Event Listeners, Frontend Components, Integration Tests, etc. - Total 15 tasks]*

**Total Estimated Effort:** 120-140 hours (3-4 weeks with 1 engineer)

**Critical Path:**
1. Database → Constants → Engine (foundational, must be first)
2. Service Layer → API Endpoints (backend complete)
3. Event Listeners (smart refresh)
4. Frontend components (parallel after API ready)
5. Integration tests → User acceptance

**Dependencies:**
- Task 1 blocks all others (database required)
- Tasks 2-3 must be sequential (engine needs constants)
- Task 4 (service) needs 1-3 complete
- Tasks 5-6 (API) need task 4
- Task 7 (events) needs task 4
- Frontend tasks (8-11) need API complete (task 6)
- Testing tasks (12-14) need everything else

**Parallel Opportunities:**
- After API complete: Frontend + Event listeners can be parallel
- Frontend components (8-11) are mostly independent
- Unit tests can be written alongside implementation
