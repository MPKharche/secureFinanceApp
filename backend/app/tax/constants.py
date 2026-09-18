"""Tax constants for FY 2026-27."""
from decimal import Decimal

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

# ============================================================================
# CAPITAL GAINS TAX CONSTANTS
# ============================================================================

# Holding period thresholds (in months)
EQUITY_HOLDING_PERIOD_MONTHS = 12
DEBT_HOLDING_PERIOD_MONTHS = 36

# Asset classifications
EQUITY_ASSET_TYPES = {
    "equity",
    "mutual_fund",  # Equity-oriented mutual funds
    "stock",
    "etf",
}

# Capital Gains Tax rates
EQUITY_STCG_RATE = Decimal("0.15")  # 15% for short-term equity gains
EQUITY_LTCG_RATE = Decimal("0.10")  # 10% for long-term equity gains above exemption
DEBT_LTCG_RATE = Decimal("0.20")    # 20% with indexation for debt LTCG

# Exemptions
EQUITY_LTCG_EXEMPTION = Decimal("100000")  # ₹1,00,000 exemption for equity LTCG

# Advance tax
ADVANCE_TAX_THRESHOLD = Decimal("10000")  # Threshold for advance tax requirement

ADVANCE_TAX_SCHEDULE = [
    {"due_date": "2026-06-15", "cumulative_percent": Decimal("0.15")},  # 15% by June 15
    {"due_date": "2026-09-15", "cumulative_percent": Decimal("0.45")},  # 45% by Sep 15
    {"due_date": "2026-12-15", "cumulative_percent": Decimal("0.75")},  # 75% by Dec 15
    {"due_date": "2027-03-15", "cumulative_percent": Decimal("1.00")},  # 100% by Mar 15
]
