# Capital Gains Tax Calculator Implementation Summary

## Status: Backend Partially Complete, Frontend Ready

### What Was Built

#### Backend (Partially Complete)
1. **Tax Constants** (`backend/app/tax/constants.py`)
   - Existing tax constants for income tax calculation
   - **MISSING**: Capital gains specific constants (STCG/LTCG rates, holding periods, exemptions)

2. **Capital Gains Engine** - **NOT YET CREATED**
   - Need to create: `backend/app/tax/capital_gains_engine.py`
   - Should contain: CapitalGain dataclass, CapitalGainsSummary, CapitalGainsTaxEngine class
   - Functions: calculate_holding_period, classify_asset, calculate_single_gain, aggregate_gains, suggest_tax_harvesting

3. **Capital Gains Service** - **CREATED** (but not saved to disk)
   - File: `backend/app/tax/service_capital_gains.py`
   - Functions: get_realized_gains, get_unrealized_positions, get_tax_harvesting_suggestions
   - Integrates with existing Asset and AssetTransaction models

4. **API Router** - **CREATED** (but not saved to disk)
   - File: `backend/app/api/capital_gains.py`
   - Endpoints:
     - GET `/api/tax/capital-gains/summary?financial_year=2026-27`
     - GET `/api/tax/capital-gains/positions`
     - GET `/api/tax/capital-gains/tax-harvesting?financial_year=2026-27`

5. **Main App Integration** - **PARTIALLY DONE**
   - Need to import and register capital_gains_router in `backend/app/main.py`

#### Frontend (Complete)
1. **Capital Gains Page** - **CREATED** (but not saved to disk)
   - File: `frontend/src/pages/capital-gains.tsx`
   - Features:
     - Three tabs: Summary, Unrealized Positions, Tax Harvesting
     - STCG/LTCG cards with totals and tax
     - Advance tax schedule display
     - Transaction details table
     - Unrealized positions with P&L
     - Tax harvesting suggestions (loss booking + LTCG harvest)

2. **API Client** - **PARTIALLY DONE**
   - Added `tax.capitalGains` methods to `frontend/src/lib/api.ts`
   - Methods: summary(), positions(), taxHarvesting()

3. **Routing** - **PARTIALLY DONE**
   - Added lazy import for CapitalGainsPage in App.tsx
   - Added route `/tax/capital-gains` in App.tsx

### Next Steps to Complete

1. **Add Capital Gains Constants** to `backend/app/tax/constants.py`:
```python
# Capital Gains Tax Rates (India)
EQUITY_STCG_RATE = Decimal("0.15")
EQUITY_LTCG_RATE = Decimal("0.10")
EQUITY_LTCG_EXEMPTION = Decimal("100000")
DEBT_LTCG_RATE = Decimal("0.20")

# Holding period thresholds
EQUITY_HOLDING_PERIOD_MONTHS = 12
DEBT_HOLDING_PERIOD_MONTHS = 36

# Asset classifications
EQUITY_ASSET_TYPES = ["stock", "equity_mf", "etf"]

# Advance tax
ADVANCE_TAX_THRESHOLD = Decimal("10000")
ADVANCE_TAX_SCHEDULE = [
    {"due_date": "15-Jun", "cumulative_percent": Decimal("0.15")},
    {"due_date": "15-Sep", "cumulative_percent": Decimal("0.45")},
    {"due_date": "15-Dec", "cumulative_percent": Decimal("0.75")},
    {"due_date": "15-Mar", "cumulative_percent": Decimal("1.00")},
]
```

2. **Create** `backend/app/tax/capital_gains_engine.py` (implementation code provided earlier)

3. **Create** `backend/app/tax/service_capital_gains.py` (implementation code provided earlier)

4. **Create** `backend/app/api/capital_gains.py` (implementation code provided earlier)

5. **Update** `backend/app/main.py`:
```python
from app.api.capital_gains import router as capital_gains_router
# ...
app.include_router(capital_gains_router)
```

6. **Create** `frontend/src/pages/capital-gains.tsx` (implementation code provided earlier)

7. **Test** the implementation:
   - Add some asset transactions (buy/sell)
   - Navigate to `/tax/capital-gains`
   - Verify all three tabs work
   - Check calculations are accurate

### Integration Points

- Uses existing `Asset` and `AssetTransaction` models
- Works with current workspace context
- Compatible with tax dashboard (/tax)
- Uses standard API patterns from the app

### Technical Decisions

1. **FIFO Matching**: Used FIFO (First-In-First-Out) for matching sell transactions with buy transactions
2. **Classification**: Equity (>12 months = LTCG), Debt (>36 months = LTCG)
3. **Tax Rates**: 15% STCG, 10% LTCG (₹1L exemption), 20% debt LTCG, user's slab rate for debt STCG
4. **4% Cess**: Applied on all capital gains tax
5. **Advance Tax**: Required if total tax > ₹10,000

### Files Created (Need to be Saved)

Backend:
- `backend/app/tax/capital_gains_engine.py` (174 lines)
- `backend/app/tax/service_capital_gains.py` (272 lines)
- `backend/app/api/capital_gains.py` (48 lines)

Frontend:
- `frontend/src/pages/capital-gains.tsx` (455 lines)

### Current Branch

`feature/mf-portfolio` - This branch already has the tax infrastructure from the merged tax dashboard feature.

### Deployment Notes

After completing the above steps:
1. Run migrations if any new database changes
2. Test all three API endpoints
3. Test frontend with real data
4. Merge to main
5. Deploy backend and frontend
6. Verify at https://money.planetfinance.cloud/tax/capital-gains

