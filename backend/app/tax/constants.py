"""Tax constants for FY 2026-27 (Indian tax regime)."""

from decimal import Decimal

CURRENT_FY = "2026-27"

# Capital Gains Tax Rates (India)
EQUITY_STCG_RATE = Decimal("0.15")
EQUITY_LTCG_RATE = Decimal("0.10")
EQUITY_LTCG_EXEMPTION = Decimal("100000")

DEBT_LTCG_RATE = Decimal("0.20")

# Holding period thresholds
EQUITY_HOLDING_PERIOD_MONTHS = 12
DEBT_HOLDING_PERIOD_MONTHS = 36

# Cess
CESS_RATE = Decimal("0.04")

# Asset classifications
EQUITY_ASSET_TYPES = ["stock", "equity_mf", "etf"]
DEBT_ASSET_TYPES = ["bond", "debt_mf", "fd", "other"]

# Advance tax thresholds
ADVANCE_TAX_THRESHOLD = Decimal("10000")

# Advance tax due dates
ADVANCE_TAX_SCHEDULE = [
    {"due_date": "15-Jun", "cumulative_percent": Decimal("0.15")},
    {"due_date": "15-Sep", "cumulative_percent": Decimal("0.45")},
    {"due_date": "15-Dec", "cumulative_percent": Decimal("0.75")},
    {"due_date": "15-Mar", "cumulative_percent": Decimal("1.00")},
]
