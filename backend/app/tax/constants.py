"""Constants for capital gains tax calculations."""
from decimal import Decimal

# Current financial year
CURRENT_FY = "2026-27"

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

# Tax rates
EQUITY_STCG_RATE = Decimal("0.15")  # 15% for short-term equity gains
EQUITY_LTCG_RATE = Decimal("0.10")  # 10% for long-term equity gains above exemption
DEBT_LTCG_RATE = Decimal("0.20")    # 20% with indexation for debt LTCG

# Exemptions
EQUITY_LTCG_EXEMPTION = Decimal("100000")  # ₹1,00,000 exemption for equity LTCG

# Cess
CESS_RATE = Decimal("0.04")  # 4% health and education cess

# Advance tax
ADVANCE_TAX_THRESHOLD = Decimal("10000")  # Threshold for advance tax requirement

ADVANCE_TAX_SCHEDULE = [
    {"due_date": "2026-06-15", "cumulative_percent": Decimal("0.15")},  # 15% by June 15
    {"due_date": "2026-09-15", "cumulative_percent": Decimal("0.45")},  # 45% by Sep 15
    {"due_date": "2026-12-15", "cumulative_percent": Decimal("0.75")},  # 75% by Dec 15
    {"due_date": "2027-03-15", "cumulative_percent": Decimal("1.00")},  # 100% by Mar 15
]
