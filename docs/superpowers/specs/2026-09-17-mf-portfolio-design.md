# Mutual Fund Portfolio with CAS Import — Design Specification

**Priority:** P0 (score 18/20)  
**Date:** 2026-09-17  
**Status:** Design phase

## Executive Summary

This specification extends Securo's existing investment ledger (RFC #235) to become a best-in-class mutual fund portfolio tracker for the Indian market. The centerpiece is **CAS (Consolidated Account Statement) import** from CAMS/KFintech, which brings all MF holdings and transactions into Securo in seconds. We add **XIRR calculation** for accurate SIP returns, **SIP calendar** for tracking recurring investments, **goal mapping** to link MF investments to financial goals, and **tax loss harvesting alerts** to optimize tax liability.

**Market context:** Kuvera leads with CAS import + clean portfolio view. Groww offers Active vs Lifetime XIRR and SIP tracking. ET Money has tax harvesting. INDmoney aggregates across platforms. Securo already has the foundation (asset tracking with average price, ledger transactions, goal tracking) — we need India-specific MF features layered on top.

## Problem Statement

Indian mutual fund investors face three pain points:

1. **Manual data entry hell:** Tracking MF across 5 AMCs means typing dozens of transactions. CAS PDF has everything but no app imports it well.
2. **Wrong return calculations:** Simple CAGR doesn't work for SIPs. XIRR is the standard but most apps calculate it wrong or show only one view.
3. **Tax blindness:** LTCG >₹1.25L is taxable. Investors miss harvest opportunities because they don't track gains per scheme.

Securo solves #1 with CAS import, #2 with proper XIRR (both active and lifetime), #3 with automated harvest alerts.

## User Needs (from research)

### Primary (P0)

- **CAS import:** Upload CAMS/KFintech PDF → instant portfolio sync
- **XIRR calculation:** Show real SIP returns (not fake CAGR)
- **SIP tracking:** Calendar view, autopay alerts, missed SIP warnings
- **Current portfolio view:** Holdings, current value, unrealized gains
- **Transaction history:** All buys/sells/switches with dates and NAV
- **Goal mapping:** Link schemes to goals (retirement, house, child education)
- **Tax loss harvesting alerts:** Flag schemes with losses >10% and LTCG harvest opportunities

### Secondary (P1)

- **Fund comparison:** Compare 2-3 schemes side-by-side (returns, expense ratio, AUM)
- **SIP calculator:** How much to invest monthly to reach goal
- **Direct plan alerts:** Warn if holding regular plan (higher expense ratio)
- **Dividend tracking:** Log dividend payouts per scheme
- **Portfolio X-ray:** Asset allocation across equity/debt/hybrid
- **Benchmark comparison:** Scheme return vs Nifty/Sensex/category average

### Out of scope (for now)

- **Live NAV sync:** Manual NAV entry or CSV import only (no API initially)
- **AMC portal integration:** User must download CAS themselves
- **SIP auto-debit:** No bank integration; reminder only
- **Tax filing export:** Basic CSV; no ITR XML generation

## Market Leaders — What They Do Well

### Kuvera (best CAS import)
- Email CAS request → CAMS/KFintech sends PDF → upload to app → done
- Shows XIRR per scheme, portfolio XIRR, goal-wise XIRR
- Clean portfolio card: scheme name, units, current value, 1Y return, XIRR
- SIP book: all active SIPs with next date, amount, status
- Tax harvesting: lists schemes with unrealized gains >₹1L (LTCG limit)

### Groww (best XIRR display)
- **Active XIRR:** Return since last buy (useful for recent investors)
- **Lifetime XIRR:** Return since first transaction (true performance)
- Both shown side-by-side on scheme card
- Portfolio timeline: visual chart of investments vs current value

### ET Money (best tax tools)
- Tax loss harvesting dashboard: schemes to sell for losses
- LTCG harvest calculator: how much to redeem to stay under ₹1.25L
- Tax report: realized gains YTD, split STCG/LTCG

### INDmoney (best aggregation)
- Multi-platform: import from Kuvera, Groww, Paytm Money
- Unified portfolio view across all platforms
- NetWorth tracker includes MF + stocks + FD + real estate

## What Securo Already Has (RFC #235)

✅ **Asset tracking:** `assets` table with `units`, `average_price`, `purchase_price` (cost basis)  
✅ **Transaction ledger:** `asset_transactions` with buy/sell, quantity, price, fee, date  
✅ **Weighted average:** Calculates preço médio (average price) automatically  
✅ **Realized gains:** Tracks sold position P&L  
✅ **Unrealized gains:** `current_value - cost_basis`  
✅ **Goal tracking:** Goals can track assets or asset groups  
✅ **Multi-wallet:** Separate holdings per account/folio

**What we're adding:** CAS parser, XIRR engine, SIP calendar, MF-specific UI, tax alerts, goal-MF linking

## Design Approach

### Three-layer architecture

```
┌─────────────────────────────────────────────┐
│  User uploads CAS PDF                       │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  CAS Parser (Python)                        │
│  - Reads PDF text (pypdf or pdfplumber)    │
│  - Extracts folio, scheme, transactions    │
│  - Normalizes AMC names, ISIN              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  MF Service (business logic)                │
│  - Find-or-create scheme asset             │
│  - Upsert transactions (idempotent)        │
│  - Recalculate average price, units        │
│  - Calculate XIRR (Newton-Raphson)         │
│  - Detect SIPs (recurring buys)            │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Storage (PostgreSQL)                       │
│  - assets (MF schemes, type=mutual_fund)   │
│  - asset_transactions (all buys/sells)     │
│  - mutual_fund_sips (SIP definitions)      │
│  - mutual_fund_metadata (AMC, category)    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Frontend (React)                           │
│  - Portfolio page: holdings grid           │
│  - SIP calendar: upcoming SIPs             │
│  - Tax dashboard: harvest opportunities    │
└─────────────────────────────────────────────┘
```

### Core Components

#### 1. CAS Parser (`backend/app/services/cas_parser.py`)

**Input:** PDF bytes from CAMS/KFintech  
**Output:** Structured JSON with folios, schemes, transactions

**Parsing strategy:**
- **CAMS format:** Text-based, table structure, headers like "Folio No", "Scheme Name", "Transaction Date"
- **KFintech format:** Similar but different column order, sometimes nested tables
- Use `pdfplumber` (better table extraction than pypdf)
- Regex patterns to extract:
  - Folio number: `Folio No: 12345/67` or `Folio: 12345/67`
  - Scheme name: Line after folio, before transaction table
  - ISIN: `INF...` pattern (12-char alphanumeric)
  - Transactions: Date, description, amount, units, NAV, balance
  - Transaction type: "Purchase", "Additional Purchase", "Redemption", "Switch In/Out", "Dividend Reinvest"

**Normalization:**
- AMC name variations: "ICICI Prudential Mutual Fund" vs "ICICI Pru MF" → normalize to canonical name
- Scheme name cleanup: Remove "(Regular Plan)" suffix, trim whitespace
- Transaction type mapping:
  - "Purchase", "Additional Purchase" → `buy`
  - "Redemption", "Switch Out" → `sell`
  - "Switch In" → `buy` (to receiving scheme)
  - "Dividend Reinvest" → `buy` (units added, no cash flow)

**Error handling:**
- Invalid PDF → clear error message, suggest CAMS format
- Parsing failure → log raw text, return partial results if any
- Duplicate detection: check existing transactions by folio + date + amount

#### 2. XIRR Calculator (`backend/app/services/xirr_calculator.py`)

**XIRR (Extended Internal Rate of Return):** The annualized return rate that makes NPV of all cash flows = 0.

Formula: `Σ (cash_flow_i / (1 + XIRR)^((date_i - start_date).days / 365)) = 0`

**Implementation:** Newton-Raphson method (iterative)
- Start with guess = 0.1 (10%)
- Iterate: `XIRR_new = XIRR_old - f(XIRR_old) / f'(XIRR_old)`
- Stop when |change| < 0.0001 or 100 iterations
- If doesn't converge, return None (happens with weird cash flow patterns)

**Cash flows for MF:**
- **Buy:** Negative (money out) on transaction date
- **Sell:** Positive (money in) on transaction date
- **Current holding:** Positive (current value) on today's date

**Two XIRR views (Groww's innovation):**
1. **Active XIRR:** From most recent buy to today
   - Use case: "I started investing 6 months ago, what's my return?"
   - Cash flows: last buy + all subsequent buys + current value
2. **Lifetime XIRR:** From first transaction to today
   - Use case: "What's the true performance over 5 years?"
   - Cash flows: all transactions + current value

**Example calculation:**
```
Scheme: ICICI Pru Bluechip (₹10,000 SIP)
Transactions:
  2024-01-05: Buy ₹10,000 (NAV ₹50, units 200)
  2024-02-05: Buy ₹10,000 (NAV ₹52, units 192.31)
  2024-03-05: Buy ₹10,000 (NAV ₹55, units 181.82)
Current (2024-04-05): 574.13 units × ₹58 = ₹33,300

Cash flows for Lifetime XIRR:
  2024-01-05: -₹10,000
  2024-02-05: -₹10,000
  2024-03-05: -₹10,000
  2024-04-05: +₹33,300
XIRR ≈ 48% (annualized)

Cash flows for Active XIRR (from last buy):
  2024-03-05: -₹10,000
  2024-04-05: +₹11,076 (181.82 units × ₹58)
XIRR ≈ 10.76% over 1 month → annualized ≈ 144% (misleading for short periods)
```

**Gotchas:**
- XIRR is meaningless for <6 months (annualization magnifies small changes)
- Show "N/A" if holding period < 180 days
- XIRR can be negative (losses)
- Dividend reinvest: doesn't add to cash flow (units change but no money in/out)

#### 3. SIP Detection & Calendar (`backend/app/services/sip_service.py`)

**SIP = Systematic Investment Plan:** Recurring monthly buy of fixed amount.

**Detection logic:**
- Group transactions by scheme
- Find sequences of buys with:
  - Same amount (±5% tolerance for NAV rounding)
  - Regular interval (28-32 days = monthly, 88-92 days = quarterly)
  - At least 3 consecutive transactions
- Extract: amount, frequency, start date, last date

**Storage:** New table `mutual_fund_sips`
```sql
CREATE TABLE mutual_fund_sips (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    asset_id UUID NOT NULL REFERENCES assets(id),
    amount DECIMAL(18, 2) NOT NULL,
    frequency VARCHAR(20) NOT NULL,  -- monthly, quarterly
    start_date DATE NOT NULL,
    end_date DATE,  -- NULL if active
    status VARCHAR(20) NOT NULL,  -- active, paused, completed
    next_due_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**SIP Calendar view:**
- List all active SIPs sorted by next_due_date
- Show: scheme name, amount, frequency, next date, status
- Badge colors: green (on track), yellow (due in 3 days), red (missed)
- Action: mark as "paid" → creates new transaction, updates next_due_date

**Missed SIP detection:**
- Cron job (daily): check SIPs where next_due_date < today - 7 days
- If no matching transaction found in last 10 days → status = "missed"
- Frontend shows "Missed SIP" badge

#### 4. Goal-MF Mapping (extend existing goals)

Securo already has goal tracking with `goal.tracking_method = 'asset'` and `goal.asset_id`.

**Enhancement:** Allow multiple assets per goal (many-to-many)

New table:
```sql
CREATE TABLE goal_assets (
    id UUID PRIMARY KEY,
    goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    allocated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(goal_id, asset_id)
);
```

**UI changes:**
- Goal edit page: "Add MF Scheme" button → search and link
- MF portfolio page: column shows goal badge/tag per scheme
- Goal progress: sum current_value of all linked schemes

**Use case:**
- Goal: "Child Education ₹50L by 2035"
- Linked schemes:
  - ICICI Pru Bluechip (₹10k SIP) → ₹2.5L current
  - HDFC Balanced Advantage (₹5k SIP) → ₹1.2L current
- Progress: ₹3.7L / ₹50L = 7.4%

#### 5. Tax Loss Harvesting Alerts

**Tax context (India):**
- **LTCG (Long-Term Capital Gains):** Gains on equity MF held >1 year
  - Tax: 12.5% on gains >₹1.25L per year
  - Strategy: Harvest gains up to ₹1.25L yearly (sell + rebuy) to reset cost basis
- **STCG (Short-Term Capital Gains):** Gains on MF held <1 year
  - Tax: 20%
  - Strategy: Hold till LTCG or harvest losses to offset other STCG

**Harvest opportunities (alerts):**

1. **LTCG harvest (annual):**
   - Find schemes with unrealized LTCG where:
     - `holding_period > 365 days`
     - `unrealized_gain > ₹50,000` (worth the effort)
     - `total_harvested_this_FY < ₹1,25,000`
   - Alert: "You can harvest ₹X in LTCG tax-free. Schemes: [list]"
   - Action: Redeem → rebuy next day (resets cost basis, no tax)

2. **Loss harvesting (opportunistic):**
   - Find schemes with unrealized loss >10%
   - If user has other gains, suggest selling to offset
   - Alert: "Scheme XYZ is down 12%. Sell to offset gains from ABC?"

3. **Direct plan switch:**
   - Find schemes with "Regular Plan" in name
   - Calculate cost: expense ratio difference × corpus
   - Alert: "Switching to Direct Plan saves ₹X per year"

**Tax dashboard page:**
- YTD realized gains: STCG, LTCG
- Harvesting opportunities: schemes + amount
- Tax liability estimate: `gains × tax_rate`
- Action buttons: "Harvest this scheme" → shows sell order preview

## Data Model (new tables + extensions)

### New table: `mutual_fund_metadata`

Store AMC and scheme reference data (seeded, not user-generated).

```sql
CREATE TABLE mutual_fund_metadata (
    id UUID PRIMARY KEY,
    isin VARCHAR(12) UNIQUE NOT NULL,  -- ISIN code
    scheme_name VARCHAR(200) NOT NULL,
    amc_name VARCHAR(100) NOT NULL,  -- Asset Management Company
    category VARCHAR(50),  -- Equity, Debt, Hybrid, etc.
    sub_category VARCHAR(50),  -- Large Cap, Mid Cap, etc.
    plan_type VARCHAR(20),  -- Direct, Regular
    expense_ratio DECIMAL(5, 4),  -- e.g., 0.0150 = 1.5%
    aum DECIMAL(18, 2),  -- Assets Under Management (₹ crores)
    launch_date DATE,
    last_updated TIMESTAMP DEFAULT NOW()
);
```

**Seed data:** AMFI (Association of Mutual Funds in India) publishes daily NAV + scheme master. One-time import of ~8000 schemes.

### Extension: `assets` table

Add MF-specific columns (nullable, only for `asset_type = 'mutual_fund'`):

```sql
ALTER TABLE assets ADD COLUMN folio_number VARCHAR(50);
ALTER TABLE assets ADD COLUMN isin VARCHAR(12);
ALTER TABLE assets ADD COLUMN scheme_code VARCHAR(50);
ALTER TABLE assets ADD COLUMN amc_name VARCHAR(100);
ALTER TABLE assets ADD COLUMN plan_type VARCHAR(20);  -- Direct, Regular
ALTER TABLE assets ADD COLUMN current_nav DECIMAL(18, 6);
ALTER TABLE assets ADD COLUMN nav_date DATE;
```

### New table: `mutual_fund_sips` (already described above)

### New table: `goal_assets` (already described above)

## API Endpoints

### CAS Import

```
POST /api/mutual-funds/cas-import
Request: multipart/form-data
  - file: CAS PDF
  - wallet_id: UUID (optional, defaults to default wallet)
Response: {
  "folios_imported": 3,
  "schemes_imported": 12,
  "transactions_imported": 145,
  "errors": [],
  "summary": [
    {
      "folio": "12345/67",
      "scheme_name": "ICICI Pru Bluechip Direct",
      "units": 1250.45,
      "current_value": 125000.00,
      "transactions": 24
    }
  ]
}
```

### Portfolio Summary

```
GET /api/mutual-funds/portfolio
Response: {
  "total_invested": 500000.00,
  "current_value": 625000.00,
  "unrealized_gain": 125000.00,
  "xirr_lifetime": 0.148,  // 14.8%
  "holdings": [
    {
      "asset_id": "uuid",
      "scheme_name": "ICICI Pru Bluechip Direct",
      "folio": "12345/67",
      "units": 1250.45,
      "average_price": 40.00,
      "current_nav": 50.00,
      "current_value": 62522.50,
      "invested": 50000.00,
      "unrealized_gain": 12522.50,
      "unrealized_gain_pct": 0.250,
      "xirr_lifetime": 0.18,
      "xirr_active": 0.12,
      "goal_name": "Retirement",
      "plan_type": "Direct"
    }
  ]
}
```

### SIP Calendar

```
GET /api/mutual-funds/sips
Response: {
  "active_sips": [
    {
      "sip_id": "uuid",
      "asset_id": "uuid",
      "scheme_name": "ICICI Pru Bluechip Direct",
      "amount": 10000.00,
      "frequency": "monthly",
      "next_due_date": "2026-10-05",
      "last_paid_date": "2026-09-05",
      "status": "active",  // active, missed, paused
      "total_invested": 120000.00,
      "sip_count": 12
    }
  ]
}

POST /api/mutual-funds/sips/{sip_id}/mark-paid
Request: {
  "transaction_date": "2026-09-17",
  "amount": 10000.00,
  "nav": 50.50
}
Response: {
  "transaction_id": "uuid",
  "next_due_date": "2026-10-17"
}
```

### Tax Harvesting

```
GET /api/mutual-funds/tax-opportunities
Response: {
  "ltcg_harvest": {
    "available_exemption": 125000.00,  // ₹1.25L limit
    "used_this_fy": 0.00,
    "opportunities": [
      {
        "asset_id": "uuid",
        "scheme_name": "ICICI Pru Bluechip",
        "unrealized_gain": 80000.00,
        "holding_period_days": 450,
        "suggested_action": "Harvest full gain (tax-free)"
      }
    ]
  },
  "loss_harvest": {
    "opportunities": [
      {
        "asset_id": "uuid",
        "scheme_name": "HDFC Small Cap",
        "unrealized_loss": -15000.00,
        "loss_pct": -12.5,
        "suggested_action": "Book loss to offset other gains"
      }
    ]
  },
  "direct_plan_switches": [
    {
      "asset_id": "uuid",
      "scheme_name": "ICICI Pru Bluechip Regular",
      "corpus": 100000.00,
      "expense_ratio_regular": 0.02,
      "expense_ratio_direct": 0.005,
      "annual_savings": 1500.00
    }
  ]
}
```

## Frontend Components

### 1. Portfolio Page (new `/mutual-funds` route)

**Layout:** Similar to Assets page but MF-optimized

**Top cards:**
- Total invested
- Current value
- Unrealized gain (absolute + %)
- Portfolio XIRR

**Holdings table:**
Columns: Scheme Name, Folio, Units, Avg Price, Current NAV, Current Value, Unrealized Gain, XIRR (Lifetime), XIRR (Active), Goal, Actions

**Filters:**
- AMC dropdown (all / ICICI / HDFC / etc.)
- Category (Equity / Debt / Hybrid)
- Plan type (Direct / Regular)
- Goal (all / Retirement / House / etc.)

**Actions:**
- Upload CAS button (prominent, top-right)
- Export CSV
- Add manual transaction (if user doesn't have CAS)

### 2. SIP Calendar Page (new `/mutual-funds/sips` route)

**Layout:** Calendar view (month grid) + list view toggle

**Calendar view:**
- Each date shows SIP icons for schemes due
- Color coding: green (paid), yellow (upcoming 3 days), red (missed)
- Click date → modal with SIPs due, "Mark as Paid" button

**List view:**
- Table: Scheme, Amount, Frequency, Next Due, Status, Actions
- Sort by: Next Due (default), Amount, Scheme Name
- Filter: Active / Paused / Missed

**Add SIP modal:**
- Select scheme (from existing holdings)
- Amount, Frequency (monthly/quarterly), Start Date
- Auto-detect option: "Detect from past transactions"

### 3. Tax Dashboard Page (new `/mutual-funds/tax` route)

**Section 1: YTD Summary**
- Cards: Total STCG, Total LTCG, Tax Liability, Harvested Gains

**Section 2: Harvest Opportunities**
- Tabs: LTCG Harvest, Loss Harvest, Direct Plan Switch
- Each tab shows table of opportunities with "Take Action" button

**Section 3: Tax Calendar**
- Timeline: Advance tax due dates (Jun 15, Sep 15, Dec 15, Mar 15)
- Shows estimated tax liability for each quarter

### 4. CAS Import Flow

**Step 1:** Upload button → file picker (PDF only)  
**Step 2:** Processing screen (spinner + "Parsing CAS...")  
**Step 3:** Preview screen:
- Shows detected folios, schemes, transactions
- User can deselect schemes before import
- "Import" button

**Step 4:** Success screen:
- Summary: X folios, Y schemes, Z transactions
- Link to "View Portfolio"
- Option to upload another CAS (for different family member)

**Error handling:**
- Invalid PDF → "This doesn't look like a CAMS/KFintech CAS. Download guide."
- Parsing errors → Show partial results + "Some transactions couldn't be parsed. Contact support."
- Duplicate transactions → "Found X duplicate transactions (skipped)"

## Implementation Phases

### Phase 1: Core CAS Import (MVP)
**Goal:** Upload CAS, see portfolio

- [ ] CAS parser (CAMS format only, text-based parsing)
- [ ] MF metadata seed (AMFI scheme master, top 500 schemes)
- [ ] Schema migrations (mutual_fund_metadata, new asset columns)
- [ ] Backend: CAS import endpoint, portfolio summary endpoint
- [ ] Frontend: Upload CAS flow, basic portfolio table
- [ ] XIRR calculator (lifetime only)

**Deliverable:** User uploads CAS → sees holdings with current value, gains, XIRR

### Phase 2: SIP Tracking
**Goal:** See all SIPs, mark as paid

- [ ] SIP detection logic
- [ ] SIP storage (mutual_fund_sips table)
- [ ] Backend: SIP CRUD endpoints, mark-paid endpoint
- [ ] Frontend: SIP calendar (list view only), add/edit SIP
- [ ] Cron job: missed SIP detection

**Deliverable:** User sees active SIPs, gets reminded of missed SIPs

### Phase 3: Goal Mapping
**Goal:** Link schemes to goals

- [ ] goal_assets table (many-to-many)
- [ ] Backend: Link/unlink asset to goal endpoints
- [ ] Frontend: Goal selector on scheme edit, goal badge on portfolio
- [ ] Goal progress: sum linked scheme values

**Deliverable:** User links MF schemes to goals, sees progress

### Phase 4: Tax Harvesting
**Goal:** Show harvest opportunities

- [ ] Tax opportunity calculator (LTCG/loss logic)
- [ ] Backend: Tax opportunities endpoint
- [ ] Frontend: Tax dashboard page (opportunities tables)
- [ ] Tax calendar (advance tax dates)

**Deliverable:** User sees "Harvest ₹80k LTCG tax-free" alert

### Phase 5: Advanced Features (P1)
- [ ] Active XIRR (in addition to lifetime)
- [ ] SIP calendar (month grid view)
- [ ] Dividend tracking (separate transactions)
- [ ] Fund comparison (side-by-side)
- [ ] Direct plan alerts
- [ ] KFintech CAS format (in addition to CAMS)
- [ ] Portfolio X-ray (asset allocation pie chart)

## Success Metrics

**Adoption:**
- % of users who upload CAS within first week
- Avg number of schemes tracked per user

**Engagement:**
- % of users who check portfolio weekly
- SIP calendar views per user per month

**Value:**
- Tax harvesting: # of users who harvest >₹50k LTCG
- Direct plan switches: ₹ saved per user per year

**Technical:**
- CAS parse success rate >95%
- XIRR calculation error rate <1% (vs Excel XIRR)

## Open Questions

1. **NAV updates:** Manual entry in Phase 1, or scrape AMFI daily NAV?
   - **Decision:** Manual entry first. Phase 2: daily AMFI scraper (Celery task)

2. **CAS password protection:** Some CAS PDFs are password-protected (PAN-based).
   - **Decision:** Ask user for password on upload. Use `pikepdf` to decrypt.

3. **Multiple folios:** Same scheme in 2 folios (different AMCs or dates).
   - **Decision:** Treat as separate assets. User can manually merge if needed.

4. **Switch transactions:** Switch from Scheme A to Scheme B.
   - **Decision:** Create `sell` in A, `buy` in B (same transaction_date, linked via external_id)

5. **Dividend payout vs reinvestment:** Different cash flow treatment.
   - **Decision:** Reinvest = `buy` (units added, no XIRR cash flow). Payout = income transaction (not buy/sell).

6. **Goal multi-asset:** Allow linking both MF + stocks to same goal?
   - **Decision:** Yes. goal_assets works for any asset_id.

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| CAS format changes | High | Version detection + fallback to manual entry |
| XIRR calculation wrong | High | Test against Excel XIRR, 100+ test cases |
| Parsing errors | Medium | Show partial results + manual correction |
| User uploads wrong PDF | Low | Validate header text for "CAMS" or "KFintech" |
| Performance (1000+ txns) | Medium | Batch insert, index on asset_id + date |

## Dependencies

**Python libraries:**
- `pdfplumber` (PDF table extraction)
- `pikepdf` (password-protected PDF)
- `numpy` (XIRR calculation, optional for speed)

**External data:**
- AMFI scheme master (one-time seed): https://www.amfiindia.com/spages/NAVAll.txt
- AMFI daily NAV (optional, Phase 2+): same URL, daily cron

**Existing Securo features:**
- Asset tracking (RFC #235) ✅
- Transaction ledger ✅
- Goal tracking ✅
- Multi-wallet ✅

## Appendix: CAS PDF Sample Structure

### CAMS Format
```
                    CONSOLIDATED ACCOUNT STATEMENT
                    Period: 01-Apr-2023 to 31-Mar-2024
PAN: ABCDE1234F

Folio No: 12345/67
ICICI PRUDENTIAL BLUECHIP FUND - DIRECT PLAN - GROWTH

Transaction  Description          Amount     Units    NAV     Balance
Date                              (₹)                 (₹)     Units
05-Jan-24    Additional Purchase  10000.00   200.00   50.00   200.00
05-Feb-24    Additional Purchase  10000.00   192.31   52.00   392.31
```

### KFintech Format
```
KARVY COMPUTER SHARE PRIVATE LIMITED
CONSOLIDATED ACCOUNT STATEMENT

Investor: JOHN DOE
PAN: ABCDE1234F

Folio Number: 98765432
Scheme Name: HDFC EQUITY FUND - DIRECT PLAN - GROWTH

Date       Transaction Type      Amount    Units     NAV      Unit Balance
10-Jan-24  Purchase             5000.00    100.00    50.00    100.00
```

## Appendix: XIRR Formula Details

**Mathematical definition:**

XIRR solves: `Σ (CF_i / (1 + r)^((t_i - t_0) / 365)) = 0`

Where:
- `CF_i` = cash flow at time i (negative for investment, positive for redemption/current value)
- `t_i` = date of cash flow i
- `t_0` = start date (typically first investment date)
- `r` = XIRR (the rate we're solving for)

**Newton-Raphson iteration:**

```python
def xirr(cash_flows, dates, guess=0.1, max_iter=100):
    """
    cash_flows: list of amounts (negative for investments, positive for returns)
    dates: list of datetime objects corresponding to cash_flows
    """
    rate = guess
    for _ in range(max_iter):
        npv = sum(cf / (1 + rate) ** ((d - dates[0]).days / 365.0)
                  for cf, d in zip(cash_flows, dates))
        dnpv = sum(-cf * ((d - dates[0]).days / 365.0) / (1 + rate) ** (((d - dates[0]).days / 365.0) + 1)
                   for cf, d in zip(cash_flows, dates))
        
        if abs(npv) < 1e-6:  # Converged
            return rate
        
        rate = rate - npv / dnpv
    
    return None  # Did not converge
```

**Edge cases:**
- All positive or all negative cash flows → no XIRR exists
- Only one cash flow → XIRR = 0
- Holding period < 6 months → XIRR unreliable (show "N/A")

## Appendix: Indian MF Tax Rules (2024)

**Equity-oriented funds:**
- LTCG: >1 year holding, 12.5% tax on gains >₹1.25L per FY
- STCG: <1 year holding, 20% tax

**Debt-oriented funds:**
- All gains taxed as per income tax slab (no LTCG benefit after Apr 2023)

**Harvesting strategies:**
1. Annual LTCG harvest: Sell ₹1.25L gains in March, rebuy in April
2. Loss booking: Sell losers before Mar 31 to offset other gains
3. Direct plan switch: No tax event if done as "switch" (not redeem+buy)

---

**Status:** Ready for review  
**Next step:** User approval → create implementation plan
