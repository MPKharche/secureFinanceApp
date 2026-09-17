# EMI Dashboard Enhancement — Design Specification

**Priority:** P0  
**Date:** 2026-09-17  
**Status:** Design phase  
**Author:** AI Assistant

## Executive Summary

This specification adds a comprehensive EMI Dashboard to Securo's existing loan tracking, providing Indian borrowers with intelligent prepayment recommendations, debt health monitoring (DTI/FOIR), smart allocation strategies, and a unified view of all loan obligations. The dashboard surfaces as both a widget on the main dashboard and a dedicated `/loans/dashboard` page.

**Market context:** ET Money leads with EMI calendar and prepayment calculators. BankBazaar offers loan comparison and balance transfer recommendations. Paisabazaar provides DTI calculation and eligibility scoring. Securo already has loan amortization (RFC #235 design), simulations (rate change, prepayment, foreclosure), and schedule tracking—we're adding strategic intelligence on top.

## Problem Statement

Indian borrowers with multiple loans (home, car, personal) face three challenges:

1. **Prepayment paralysis:** "I have ₹2L extra. Which loan should I prepay first?" Most apps show one loan at a time; nobody compares strategies.
2. **Debt blindness:** "Is my debt healthy?" DTI (Debt-to-Income) is the standard metric but few apps calculate it. Indian banks use FOIR (Fixed Obligation to Income Ratio) for loan eligibility—users don't track it themselves.
3. **No strategic view:** Users see individual loan balances but not the complete picture: total monthly EMI burn, debt-free timeline, which loan is costing most in interest.

Securo solves #1 with hybrid prepayment recommendations (Avalanche + Snowball + Balanced strategies compared side-by-side), #2 with both DTI and FOIR calculations with Indian bank thresholds, #3 with a unified dashboard showing aggregate KPIs, timeline, priority ranking, and smart allocation simulator.

## User Needs (from clarifying questions)

### Primary (P0)

- **Dashboard widget:** Total EMI, outstanding balance, next payment, debt health score—on main dashboard
- **Dedicated page:** `/loans/dashboard` with 6 key components
- **Prepayment recommendations:** Compare Avalanche (highest interest first), Snowball (smallest balance first), Balanced (completable loans first, remainder to highest interest)
- **Debt health metrics:** Both DTI and FOIR with Indian bank thresholds (DTI <40%, FOIR <50%)
- **Smart allocation simulator:** "I have ₹X, show me savings under each strategy"
- **Priority ranking:** Visual list of loans ranked by each strategy
- **Timeline view:** Month-by-month EMI obligations, debt-free projection
- **Upcoming payments:** Next 30 days, sortable by date/amount

### Secondary (P1)

- **EMI calendar:** Month grid view with payment due dates
- **Historical tracking:** EMI paid over time, principal vs interest breakdown
- **Goal integration:** "Pay off car loan by Dec 2025" linked to goals module
- **What-if scenarios:** "If I increase home loan EMI by ₹5k, when am I debt-free?"
- **Refinance alerts:** "Current rate 9.5%, market rate 8.5%—consider refinancing"
- **Balance transfer ROI:** Calculate savings from switching lenders

### Out of scope (for now)

- **Automated EMI debit:** No bank integration; reminder only
- **Loan marketplace:** No lender comparison or application
- **Credit score tracking:** Future integration with CIBIL/Experian
- **Loan insurance:** No insurance product recommendations

## Market Leaders — What They Do Well

### ET Money (best EMI calendar)
- Calendar view: all EMIs marked on dates, color-coded by loan type
- Upcoming payments: list of next 7 days, notification on due date
- Payment history: timeline of all EMIs paid, missed, partial
- Simple prepayment calculator: amount → tenure saved or EMI reduction

### BankBazaar (best loan comparison)
- Multi-loan dashboard: all loans in one table, sortable by rate/balance/EMI
- Balance transfer calculator: current loan details → recommended lenders with savings projection
- Eligibility calculator: income + existing EMIs → max loan eligible
- Loan closure checklist: steps to foreclose each loan type

### Paisabazaar (best debt health)
- DTI meter: visual gauge showing 25% (healthy) to 60% (risky)
- FOIR calculation: separates mandatory obligations (rent, school fees) from discretionary
- Affordability score: "You can afford ₹X more EMI before hitting risk zone"
- Debt consolidation: suggests combining multiple personal loans into one

## What Securo Already Has (from codebase review)

✅ **Loan accounts:** `type = 'loan'`, fields: `emi_amount`, `interest_rate`, `tenure_months`, `disbursed_on`, `emi_day`, `original_principal`, `current_balance`  
✅ **Amortization schedules:** Full schedule with principal/interest breakdown per EMI (loan_amortization_schedules table)  
✅ **Simulations:** `LoanSimulations` component with rate change, prepayment (reduce EMI vs reduce tenure), preclosure—already showing interest saved, net savings  
✅ **Transaction linking:** Transactions can be linked to schedule entries, payment status tracking  
✅ **Loan detail page:** `/loans/{id}` with overview, schedule table, analytics, simulations

**What we're adding:** Dashboard aggregation, prepayment strategy comparison, DTI/FOIR calculation, smart allocation tool, priority ranking UI, timeline projection.

## Design Approach

### Dashboard Architecture

```
┌─────────────────────────────────────────────┐
│  Main Dashboard (/dashboard)                │
│  ┌─────────────────────────────────────┐   │
│  │ Loan Dashboard Widget               │   │
│  │ - Total EMI: ₹45,000               │   │
│  │ - Total Outstanding: ₹32L          │   │
│  │ - Next Payment: Home Loan ₹25k     │   │
│  │ - Debt Health: Moderate (DTI 38%)  │   │
│  │ [View Full Dashboard →]             │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Loans Dashboard Page (/loans/dashboard)    │
│                                              │
│  ┌──────────────────────────────────────┐  │
│  │ 1. KPI Cards (4 cards)               │  │
│  │    Total EMI, Outstanding, Paid,     │  │
│  │    Debt Health Score                 │  │
│  └──────────────────────────────────────┘  │
│                                              │
│  ┌──────────────────────────────────────┐  │
│  │ 2. Debt Health Metrics               │  │
│  │    DTI gauge, FOIR gauge, breakdown  │  │
│  └──────────────────────────────────────┘  │
│                                              │
│  ┌──────────────────────────────────────┐  │
│  │ 3. Timeline (horizontal scroll)      │  │
│  │    Month-by-month EMI obligations    │  │
│  └──────────────────────────────────────┘  │
│                                              │
│  ┌──────────────────────────────────────┐  │
│  │ 4. Prepayment Strategy Simulator     │  │
│  │    Input: ₹2L → Compare 3 strategies │  │
│  └──────────────────────────────────────┘  │
│                                              │
│  ┌──────────────────────────────────────┐  │
│  │ 5. Priority Ranking (3 tabs)         │  │
│  │    Avalanche | Snowball | Balanced   │  │
│  └──────────────────────────────────────┘  │
│                                              │
│  ┌──────────────────────────────────────┐  │
│  │ 6. Upcoming Payments (next 30 days)  │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### Core Components

#### 1. Dashboard Widget (for main dashboard)

**Component:** `LoanDashboardWidget` (already exists, enhancement needed)

**Current state** (from codebase):
- Shows: total outstanding, monthly EMI, upcoming payments, recent payments, alerts
- API: `GET /api/v1/loans/dashboard`

**Enhancements:**
- Add debt health score (DTI or FOIR, color-coded)
- Add visual gauge for debt health (green <30%, yellow 30-45%, red >45%)
- Link to full dashboard: "View Detailed Insights →"

**Mock:**
```
┌──────────────────────────────────────────┐
│ Loan Overview                            │
│                                           │
│ ₹32,45,000                 ₹45,000/mo   │
│ Total Outstanding          Monthly EMI   │
│                                           │
│ Debt Health: Moderate      DTI: 38%     │
│ ███████████░░░░░           [View Full →] │
│                                           │
│ Next Due: Home Loan ₹25,000 (Oct 5)     │
│ Recent: Car Loan ₹12,000 paid (Sep 17)  │
└──────────────────────────────────────────┘
```

#### 2. Loans Dashboard Page (`/loans/dashboard`)

New page, sits alongside existing `/loans` (list) and `/loans/{id}` (detail).

**Navigation:** Main sidebar → Loans section → "Dashboard" (new), "All Loans", "Add Loan"

**Component Structure:**

**2.1 KPI Cards (top row)**
- Card 1: **Total Monthly EMI** — sum of all active loans' emi_amount
- Card 2: **Total Outstanding** — sum of all current_balance (negative, show absolute)
- Card 3: **Principal Paid YTD** — sum of principal components from paid schedule entries this year
- Card 4: **Debt Health Score** — DTI or FOIR with color-coded badge

**2.2 Debt Health Metrics (section)**

Two gauges side-by-side:

**DTI (Debt-to-Income Ratio):**
```
Formula: (Total Monthly EMI / Monthly Gross Income) × 100
Thresholds:
  - <30%: Healthy (green)
  - 30-40%: Moderate (yellow)
  - >40%: High Risk (red)
```

**FOIR (Fixed Obligation to Income Ratio):**
```
Formula: ((Total Monthly EMI + Other Obligations) / Monthly Gross Income) × 100
Other Obligations: rent, insurance premiums, existing credit card EMIs
Thresholds (Indian banks):
  - <50%: Eligible for new loans (green)
  - 50-60%: Limited eligibility (yellow)
  - >60%: Loan rejection risk (red)
```

**User input required:**
- Monthly gross income (one-time setup, stored in user preferences or workspace settings)
- Other monthly obligations (optional, defaults to 0)

**UI:**
- Two circular gauges (using recharts PieChart or custom SVG)
- Needle pointing to current percentage
- Breakdown table below:
  - Row: Each loan with EMI amount
  - Row: Other obligations (editable inline)
  - Row: Total obligations
  - Row: Monthly income (editable)
  - Calculation: DTI %, FOIR %

**Mock:**
```
┌────────────────────────────────────────────┐
│ Debt Health Metrics                        │
│                                             │
│  DTI: 38%              FOIR: 45%           │
│  ┌──────┐              ┌──────┐            │
│  │ ⚪ 38 │              │ ⚪ 45 │            │
│  │  /100│              │  /100│            │
│  └──────┘              └──────┘            │
│  Moderate              Eligible            │
│                                             │
│  Breakdown:                                 │
│  Home Loan EMI        ₹25,000              │
│  Car Loan EMI         ₹12,000              │
│  Personal Loan EMI    ₹8,000               │
│  Other Obligations    ₹5,000 [Edit]        │
│  ─────────────────────────────              │
│  Total Obligations    ₹50,000              │
│  Monthly Income       ₹1,30,000 [Edit]     │
│  ─────────────────────────────              │
│  DTI: 38%   FOIR: 45%                      │
└────────────────────────────────────────────┘
```

**2.3 Timeline (horizontal scrollable)**

**Purpose:** Show month-by-month EMI obligations for next 12-24 months, with debt-free projection.

**Data:**
- X-axis: Months (Oct 2026, Nov 2026, ..., Sep 2028)
- Y-axis: Total EMI amount per month
- Stacked bars: each loan's EMI contribution (color-coded by loan)
- End marker: "Debt-Free" when last loan closes

**Implementation:**
- Use recharts BarChart with stacked bars
- Fetch from API: monthly EMI breakdown for each loan (from amortization schedules)
- Show projected schedule (no prepayment assumed)
- Tooltip on hover: breakdown per loan for that month

**Mock:**
```
┌──────────────────────────────────────────────────────────────────┐
│ EMI Timeline (Next 24 Months)                                    │
│                                                                   │
│ ₹50k ┤ ███                                                        │
│ ₹40k ┤ ███ ███ ███ ███ ███                                       │
│ ₹30k ┤ ███ ███ ███ ███ ███ ███ ███                              │
│ ₹20k ┤ ███ ███ ███ ███ ███ ███ ███ ███ ███ ███                  │
│ ₹10k ┤ ███ ███ ███ ███ ███ ███ ███ ███ ███ ███ ███ ███          │
│      └──────────────────────────────────────────────────────────  │
│        Oct Nov Dec Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov   │
│        2026 ▸                                  2027 ▸            │
│                                                                   │
│ Legend: ██ Home Loan  ██ Car Loan  ██ Personal Loan             │
│ Debt-Free by: March 2032 (66 months from now)                    │
└──────────────────────────────────────────────────────────────────┘
```

**2.4 Prepayment Strategy Simulator**

**Purpose:** User enters lump sum amount → see savings under 3 strategies.

**3 Strategies:**

1. **Avalanche (Highest Interest First):**
   - Sort loans by interest_rate descending
   - Allocate prepayment to highest-rate loan first, then next, etc.
   - **Why it wins:** Mathematically optimal—minimizes total interest paid

2. **Snowball (Smallest Balance First):**
   - Sort loans by current_balance ascending
   - Allocate prepayment to smallest loan first (pay it off completely), then next
   - **Why it wins:** Psychological—quick wins, reduces loan count faster

3. **Balanced (Completable First, Remainder to Highest Interest):**
   - Find loans where `prepayment_amount >= current_balance` (can be closed fully)
   - Pay off all completable loans first (sorted by balance ascending for max closures)
   - Allocate remainder to highest interest rate loan
   - **Why it wins:** Balances psychology (close loans) + math (highest interest)

**UI:**

**Input section:**
- Amount input: ₹ [______] (large number input)
- "Calculate Strategies" button

**Output section:**
- 3 cards side-by-side (or tabs on mobile)
- Each card shows:
  - Strategy name + icon
  - Total interest saved vs no prepayment
  - Months saved (debt-free date advanced by X months)
  - Loans affected (list with amounts allocated)
  - Badge: "Recommended" if it saves most interest

**Mock:**
```
┌──────────────────────────────────────────────────────────────────┐
│ Smart Allocation Simulator                                        │
│                                                                   │
│ Prepayment Amount: ₹ [2,00,000]  [Calculate Strategies]         │
│                                                                   │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│ │ Avalanche    │  │ Snowball     │  │ Balanced     │ ★ Best    │
│ │ (Math)       │  │ (Psychology) │  │ (Hybrid)     │           │
│ ├──────────────┤  ├──────────────┤  ├──────────────┤           │
│ │ Interest     │  │ Interest     │  │ Interest     │           │
│ │ Saved:       │  │ Saved:       │  │ Saved:       │           │
│ │ ₹3,45,000    │  │ ₹3,20,000    │  │ ₹3,40,000    │           │
│ │              │  │              │  │              │           │
│ │ Months       │  │ Months       │  │ Months       │           │
│ │ Saved: 18    │  │ Saved: 16    │  │ Saved: 17    │           │
│ │              │  │              │  │              │           │
│ │ Allocation:  │  │ Allocation:  │  │ Allocation:  │           │
│ │ Personal 2L  │  │ Car 1.2L     │  │ Car 1.2L     │           │
│ │ (9.5% rate)  │  │ Personal 80k │  │ (close it)   │           │
│ │              │  │              │  │ Personal 80k │           │
│ │              │  │              │  │ (highest %)  │           │
│ └──────────────┘  └──────────────┘  └──────────────┘           │
└──────────────────────────────────────────────────────────────────┘
```

**Calculation Logic (backend):**

```python
def calculate_avalanche(loans: List[Loan], amount: Decimal) -> Strategy Result:
    """Allocate to highest interest rate first."""
    sorted_loans = sorted(loans, key=lambda x: x.interest_rate, reverse=True)
    allocations = []
    remaining = amount
    
    for loan in sorted_loans:
        if remaining <= 0:
            break
        allocated = min(remaining, loan.current_balance)
        allocations.append({
            'loan_id': loan.id,
            'amount': allocated,
            'reason': f'{loan.interest_rate}% (highest rate)'
        })
        remaining -= allocated
    
    # Simulate prepayments and calculate total interest saved
    interest_saved = sum(simulate_prepayment(loan, alloc['amount']).interest_saved
                         for loan, alloc in zip(sorted_loans, allocations))
    
    return StrategyResult(
        name='Avalanche',
        allocations=allocations,
        interest_saved=interest_saved,
        months_saved=calculate_months_saved(loans, allocations)
    )

def calculate_snowball(loans: List[Loan], amount: Decimal) -> StrategyResult:
    """Allocate to smallest balance first."""
    sorted_loans = sorted(loans, key=lambda x: x.current_balance)
    allocations = []
    remaining = amount
    
    for loan in sorted_loans:
        if remaining <= 0:
            break
        allocated = min(remaining, loan.current_balance)
        allocations.append({
            'loan_id': loan.id,
            'amount': allocated,
            'reason': f'₹{loan.current_balance} (smallest balance)'
        })
        remaining -= allocated
    
    interest_saved = sum(simulate_prepayment(loan, alloc['amount']).interest_saved
                         for loan, alloc in zip(sorted_loans, allocations))
    
    return StrategyResult(
        name='Snowball',
        allocations=allocations,
        interest_saved=interest_saved,
        months_saved=calculate_months_saved(loans, allocations)
    )

def calculate_balanced(loans: List[Loan], amount: Decimal) -> StrategyResult:
    """Close completable loans first, remainder to highest interest."""
    completable = [loan for loan in loans if loan.current_balance <= amount]
    # Sort completable by balance ascending (close smallest first for max count)
    completable_sorted = sorted(completable, key=lambda x: x.current_balance)
    
    allocations = []
    remaining = amount
    
    # Phase 1: Close all completable loans
    for loan in completable_sorted:
        if remaining <= 0:
            break
        allocated = loan.current_balance  # Pay off fully
        allocations.append({
            'loan_id': loan.id,
            'amount': allocated,
            'reason': 'Close loan (completable)'
        })
        remaining -= allocated
    
    # Phase 2: Remainder to highest interest rate loan (that wasn't closed)
    if remaining > 0:
        non_completable = [loan for loan in loans if loan not in completable_sorted]
        if non_completable:
            highest_rate_loan = max(non_completable, key=lambda x: x.interest_rate)
            allocations.append({
                'loan_id': highest_rate_loan.id,
                'amount': min(remaining, highest_rate_loan.current_balance),
                'reason': f'{highest_rate_loan.interest_rate}% (highest rate)'
            })
    
    interest_saved = calculate_interest_saved(loans, allocations)
    
    return StrategyResult(
        name='Balanced',
        allocations=allocations,
        interest_saved=interest_saved,
        months_saved=calculate_months_saved(loans, allocations),
        loans_closed=len(completable_sorted)
    )
```

**2.5 Priority Ranking (3 tabs)**

**Purpose:** Show which loan to prepay first under each strategy (even without entering amount).

**UI:** 3 tabs, each shows loans ranked with visual indicators

**Tab 1: Avalanche View**
```
┌────────────────────────────────────────────┐
│ Priority: Avalanche (Highest Interest)     │
├────────────────────────────────────────────┤
│ 1. 🔴 Personal Loan               9.5%     │
│    ₹3,20,000 outstanding                   │
│    Prepay this first to save most interest │
│                                             │
│ 2. 🟡 Car Loan                    8.2%     │
│    ₹1,20,000 outstanding                   │
│                                             │
│ 3. 🟢 Home Loan                   7.5%     │
│    ₹28,00,000 outstanding                  │
└────────────────────────────────────────────┘
```

**Tab 2: Snowball View**
```
┌────────────────────────────────────────────┐
│ Priority: Snowball (Smallest Balance)      │
├────────────────────────────────────────────┤
│ 1. 🔴 Car Loan                    ₹1.2L    │
│    Close this first for quick win          │
│    Interest rate: 8.2%                     │
│                                             │
│ 2. 🟡 Personal Loan               ₹3.2L    │
│                                             │
│ 3. 🟢 Home Loan                   ₹28L     │
└────────────────────────────────────────────┘
```

**Tab 3: Balanced View**
```
┌────────────────────────────────────────────┐
│ Priority: Balanced (Completable + Math)    │
├────────────────────────────────────────────┤
│ Completable (if prepayment ≥ balance):     │
│ 1. 🔴 Car Loan                    ₹1.2L    │
│    Can be closed with ₹1.2L                │
│                                             │
│ Not completable—allocate remainder to:     │
│ 2. 🟡 Personal Loan (9.5%)        ₹3.2L    │
│    Highest interest among open loans       │
│                                             │
│ 3. 🟢 Home Loan (7.5%)            ₹28L     │
└────────────────────────────────────────────┘
```

**Implementation:**
- Read-only view (no inputs)
- Click on a loan card → navigate to `/loans/{id}` detail page
- Icon color: red (priority 1), yellow (priority 2), green (priority 3+)

**2.6 Upcoming Payments (next 30 days)**

**Purpose:** Calendar-like view of EMIs due soon, sorted by date.

**Data source:** `loan_amortization_schedules` table, filter `due_date BETWEEN today AND today+30`, status = 'scheduled'

**UI:**

Table with columns:
- Due Date
- Loan Name
- EMI Amount
- Status (color badge: green = paid, yellow = due soon <7 days, red = overdue)
- Action (Mark Paid, View Loan)

**Mock:**
```
┌──────────────────────────────────────────────────────────────┐
│ Upcoming Payments (Next 30 Days)                             │
├──────────────────────────────────────────────────────────────┤
│ Due Date  │ Loan          │ EMI Amount  │ Status    │ Action │
├───────────┼───────────────┼─────────────┼───────────┼────────┤
│ Oct 5     │ Home Loan     │ ₹25,000     │ Due Soon  │ [Pay]  │
│ Oct 8     │ Car Loan      │ ₹12,000     │ Scheduled │ [View] │
│ Oct 10    │ Personal Loan │ ₹8,000      │ Scheduled │ [View] │
│ Oct 25    │ Home Loan     │ ₹25,000     │ Scheduled │ [View] │
└──────────────────────────────────────────────────────────────┘
```

**Action: "Mark Paid"**
- Opens dialog: actual payment date, actual amount (defaults to EMI amount)
- Links to transaction if user selects one
- Updates schedule entry: `payment_status = 'paid'`, `actual_payment_date`, `actual_amount_paid`

#### 3. Pie Chart (Loan Composition)

**Purpose:** Visual breakdown of outstanding balance by loan type or individual loan.

**Two views (toggle):**

**View 1: By Loan Type**
```
Home Loan: ₹28L (86%)
Car Loan: ₹1.2L (4%)
Personal Loan: ₹3.2L (10%)
```

**View 2: By Individual Loan**
```
ICICI Home Loan: ₹28L (86%)
Kotak Car Loan: ₹1.2L (4%)
HDFC Personal Loan: ₹3.2L (10%)
```

**Implementation:**
- Recharts PieChart with labels
- Color-coded by loan type (from `loan_kind` field)
- Hover tooltip: Loan name, outstanding, percentage, interest rate

**Placement:** Either in sidebar of dashboard page, or as a card between KPIs and timeline.

## Data Model

### Existing Tables (no changes needed)

- `accounts` (type='loan'): Already has all loan fields
- `loan_amortization_schedules`: EMI schedule with due dates, amounts, status
- `loan_prepayments`: Prepayment history
- `transactions`: Linked to schedule entries for payment tracking

### New Fields (optional, for preferences)

**Workspace or User settings:**
- `monthly_gross_income`: DECIMAL(15,2) — for DTI/FOIR calculation
- `other_monthly_obligations`: DECIMAL(15,2) — rent, insurance, etc.

**Storage:** Could go in `user_preferences` JSONB field or `workspace` settings. Not critical for MVP—can be session-only (stored in frontend state, not persisted).

## API Endpoints

### Dashboard Summary

```
GET /api/v1/loans/dashboard/summary
Response: {
  "total_monthly_emi": 45000.00,
  "total_outstanding": 3245000.00,
  "principal_paid_ytd": 180000.00,
  "interest_paid_ytd": 95000.00,
  "active_loan_count": 3,
  "debt_health": {
    "dti": 0.38,  // 38%
    "foir": 0.45,  // 45%
    "monthly_income": 130000.00,  // user-provided or null
    "other_obligations": 5000.00,  // user-provided or 0
    "status": "moderate"  // healthy, moderate, high_risk
  },
  "debt_free_date": "2032-03-15",
  "months_to_debt_free": 66
}
```

### Timeline Data

```
GET /api/v1/loans/dashboard/timeline?months=24
Response: {
  "timeline": [
    {
      "month": "2026-10",
      "total_emi": 45000.00,
      "breakdown": [
        {"loan_id": "uuid1", "loan_name": "Home Loan", "emi": 25000.00},
        {"loan_id": "uuid2", "loan_name": "Car Loan", "emi": 12000.00},
        {"loan_id": "uuid3", "loan_name": "Personal Loan", "emi": 8000.00}
      ]
    },
    {
      "month": "2026-11",
      "total_emi": 45000.00,
      "breakdown": [...]
    }
    // ... 24 months
  ]
}
```

### Strategy Comparison

```
POST /api/v1/loans/dashboard/compare-strategies
Request: {
  "prepayment_amount": 200000.00
}
Response: {
  "strategies": [
    {
      "name": "avalanche",
      "interest_saved": 345000.00,
      "months_saved": 18,
      "allocations": [
        {
          "loan_id": "uuid3",
          "loan_name": "Personal Loan",
          "amount": 200000.00,
          "reason": "9.5% (highest rate)",
          "remaining_balance": 120000.00
        }
      ],
      "recommended": true
    },
    {
      "name": "snowball",
      "interest_saved": 320000.00,
      "months_saved": 16,
      "allocations": [
        {
          "loan_id": "uuid2",
          "loan_name": "Car Loan",
          "amount": 120000.00,
          "reason": "₹1.2L (smallest balance)",
          "remaining_balance": 0.00,
          "closed": true
        },
        {
          "loan_id": "uuid3",
          "loan_name": "Personal Loan",
          "amount": 80000.00,
          "reason": "₹3.2L (next smallest)",
          "remaining_balance": 240000.00
        }
      ],
      "loans_closed": 1
    },
    {
      "name": "balanced",
      "interest_saved": 340000.00,
      "months_saved": 17,
      "allocations": [
        {
          "loan_id": "uuid2",
          "loan_name": "Car Loan",
          "amount": 120000.00,
          "reason": "Close loan (completable)",
          "remaining_balance": 0.00,
          "closed": true
        },
        {
          "loan_id": "uuid3",
          "loan_name": "Personal Loan",
          "amount": 80000.00,
          "reason": "9.5% (highest rate)",
          "remaining_balance": 240000.00
        }
      ],
      "loans_closed": 1
    }
  ]
}
```

### Priority Ranking

```
GET /api/v1/loans/dashboard/priority-ranking
Response: {
  "avalanche": [
    {"rank": 1, "loan_id": "uuid3", "loan_name": "Personal Loan", "interest_rate": 9.5, "outstanding": 320000.00},
    {"rank": 2, "loan_id": "uuid2", "loan_name": "Car Loan", "interest_rate": 8.2, "outstanding": 120000.00},
    {"rank": 3, "loan_id": "uuid1", "loan_name": "Home Loan", "interest_rate": 7.5, "outstanding": 2800000.00}
  ],
  "snowball": [
    {"rank": 1, "loan_id": "uuid2", "loan_name": "Car Loan", "outstanding": 120000.00, "interest_rate": 8.2},
    {"rank": 2, "loan_id": "uuid3", "loan_name": "Personal Loan", "outstanding": 320000.00, "interest_rate": 9.5},
    {"rank": 3, "loan_id": "uuid1", "loan_name": "Home Loan", "outstanding": 2800000.00, "interest_rate": 7.5}
  ],
  "balanced": {
    "completable": [
      {"rank": 1, "loan_id": "uuid2", "loan_name": "Car Loan", "outstanding": 120000.00, "required_amount": 120000.00}
    ],
    "remainder_priority": [
      {"rank": 2, "loan_id": "uuid3", "loan_name": "Personal Loan", "interest_rate": 9.5, "outstanding": 320000.00},
      {"rank": 3, "loan_id": "uuid1", "loan_name": "Home Loan", "interest_rate": 7.5, "outstanding": 2800000.00}
    ]
  }
}
```

### Upcoming Payments

```
GET /api/v1/loans/dashboard/upcoming-payments?days=30
Response: {
  "payments": [
    {
      "schedule_entry_id": "uuid",
      "loan_id": "uuid1",
      "loan_name": "Home Loan",
      "due_date": "2026-10-05",
      "emi_amount": 25000.00,
      "principal_component": 18500.00,
      "interest_component": 6500.00,
      "payment_status": "scheduled",  // scheduled, paid, overdue
      "days_until_due": 3
    },
    // ... more payments
  ]
}
```

### Debt Health Calculation (optional endpoint if we store income)

```
POST /api/v1/loans/dashboard/calculate-debt-health
Request: {
  "monthly_income": 130000.00,
  "other_obligations": 5000.00
}
Response: {
  "dti": 0.38,
  "foir": 0.45,
  "status": "moderate",
  "breakdown": {
    "total_emi": 45000.00,
    "other_obligations": 5000.00,
    "total_obligations": 50000.00,
    "monthly_income": 130000.00
  },
  "thresholds": {
    "dti_healthy": 0.30,
    "dti_moderate": 0.40,
    "foir_healthy": 0.50,
    "foir_risky": 0.60
  },
  "recommendations": [
    "Your DTI is 38%, which is moderate. Consider keeping it below 30%.",
    "Your FOIR is 45%, which keeps you eligible for most loans (banks prefer <50%)."
  ]
}
```

## Frontend Components

### Component Tree

```
/loans/dashboard (LoansDashboardPage)
├─ KPICards
│  ├─ KPICard (Total EMI)
│  ├─ KPICard (Total Outstanding)
│  ├─ KPICard (Principal Paid YTD)
│  └─ KPICard (Debt Health Score)
├─ DebtHealthSection
│  ├─ DebtHealthGauge (DTI)
│  ├─ DebtHealthGauge (FOIR)
│  └─ DebtHealthBreakdown (table)
├─ EMITimeline
│  └─ BarChart (recharts)
├─ PrepaymentStrategySimulator
│  ├─ AmountInput
│  └─ StrategyComparisonCards
│     ├─ StrategyCard (Avalanche)
│     ├─ StrategyCard (Snowball)
│     └─ StrategyCard (Balanced)
├─ PriorityRankingTabs
│  ├─ Tab (Avalanche)
│  ├─ Tab (Snowball)
│  └─ Tab (Balanced)
├─ LoanCompositionPieChart
│  └─ PieChart (recharts)
└─ UpcomingPaymentsTable
   └─ DataTable with actions
```

### Key Components Detail

#### `KPICard.tsx`
```tsx
interface KPICardProps {
  label: string
  value: string | number
  change?: {
    value: number
    period: string
  }
  status?: 'healthy' | 'moderate' | 'risk'
  icon?: React.ReactNode
}

// Example usage:
<KPICard
  label="Debt Health Score"
  value="Moderate"
  status="moderate"
  change={{ value: -2, period: "vs last month" }}
  icon={<TrendingDown />}
/>
```

#### `DebtHealthGauge.tsx`
```tsx
interface DebtHealthGaugeProps {
  type: 'dti' | 'foir'
  percentage: number
  thresholds: {
    healthy: number
    moderate: number
    risk: number
  }
}

// Uses recharts PieChart with custom needle
// Color zones: green 0-30%, yellow 30-40%, red 40-100%
```

#### `PrepaymentStrategySimulator.tsx`
```tsx
interface Strategy {
  name: 'avalanche' | 'snowball' | 'balanced'
  interestSaved: number
  monthsSaved: number
  allocations: Array<{
    loanId: string
    loanName: string
    amount: number
    reason: string
    closed?: boolean
  }>
  loansC losed?: number
  recommended?: boolean
}

// State management:
const [amount, setAmount] = useState<string>('')
const [strategies, setStrategies] = useState<Strategy[]>([])
const [loading, setLoading] = useState(false)

// On "Calculate" click:
const handleCalculate = async () => {
  setLoading(true)
  const response = await fetch('/api/v1/loans/dashboard/compare-strategies', {
    method: 'POST',
    body: JSON.stringify({ prepayment_amount: parseFloat(amount) })
  })
  const data = await response.json()
  setStrategies(data.strategies)
  setLoading(false)
}
```

#### `PriorityRankingTabs.tsx`
```tsx
interface RankedLoan {
  rank: number
  loanId: string
  loanName: string
  outstanding: number
  interestRate: number
  reason?: string
}

// Tabs component with 3 views
// Each view shows ranked list of loans with visual priority indicators
// Click on loan → navigate to /loans/{id}
```

## Calculations & Algorithms

### DTI Calculation

```python
def calculate_dti(loans: List[Loan], monthly_income: Decimal) -> Decimal:
    """
    DTI (Debt-to-Income Ratio) = Total Monthly EMI / Monthly Gross Income
    """
    if monthly_income <= 0:
        return Decimal('0')
    
    total_emi = sum(loan.emi_amount for loan in loans if not loan.is_closed)
    dti = (total_emi / monthly_income) * 100
    
    return dti.quantize(Decimal('0.01'))

def get_dti_status(dti: Decimal) -> str:
    """Categorize DTI into health buckets."""
    if dti < 30:
        return 'healthy'
    elif dti < 40:
        return 'moderate'
    else:
        return 'high_risk'
```

### FOIR Calculation

```python
def calculate_foir(
    loans: List[Loan],
    monthly_income: Decimal,
    other_obligations: Decimal = Decimal('0')
) -> Decimal:
    """
    FOIR (Fixed Obligation to Income Ratio) = 
    (Total Monthly EMI + Other Obligations) / Monthly Gross Income
    
    Other obligations: rent, insurance premiums, credit card EMIs, etc.
    """
    if monthly_income <= 0:
        return Decimal('0')
    
    total_emi = sum(loan.emi_amount for loan in loans if not loan.is_closed)
    total_obligations = total_emi + other_obligations
    foir = (total_obligations / monthly_income) * 100
    
    return foir.quantize(Decimal('0.01'))

def get_foir_status(foir: Decimal) -> str:
    """Indian bank thresholds."""
    if foir < 50:
        return 'healthy'  # Eligible for new loans
    elif foir < 60:
        return 'moderate'  # Limited eligibility
    else:
        return 'high_risk'  # Loan rejection risk
```

### Strategy Comparison Algorithm

```python
def compare_prepayment_strategies(
    loans: List[Loan],
    prepayment_amount: Decimal
) -> Dict[str, StrategyResult]:
    """
    Calculate all 3 strategies and return comparison.
    """
    results = {
        'avalanche': calculate_avalanche(loans, prepayment_amount),
        'snowball': calculate_snowball(loans, prepayment_amount),
        'balanced': calculate_balanced(loans, prepayment_amount)
    }
    
    # Mark recommended strategy (highest interest saved)
    max_savings = max(r.interest_saved for r in results.values())
    for name, result in results.items():
        if result.interest_saved == max_savings:
            result.recommended = True
    
    return results

def calculate_interest_saved(
    loans: List[Loan],
    allocations: List[Dict]
) -> Decimal:
    """
    For each allocation, simulate prepayment and sum interest saved.
    Uses existing LoanSimulations.simulateEarlyPayment logic.
    """
    total_saved = Decimal('0')
    
    for alloc in allocations:
        loan = next(l for l in loans if l.id == alloc['loan_id'])
        
        # Call existing prepayment simulation
        simulation = simulate_prepayment(
            account_id=loan.id,
            prepayment_amount=alloc['amount'],
            prepayment_date=datetime.now().date(),
            method='reduce_tenure'  # Always use tenure reduction for max savings
        )
        
        # Add interest saved from this prepayment
        total_saved += simulation['reduce_tenure']['interest_saved']
    
    return total_saved

def calculate_months_saved(
    loans: List[Loan],
    allocations: List[Dict]
) -> int:
    """
    Calculate how many months earlier debt-free date becomes.
    """
    # Original debt-free date (no prepayment)
    original_max_months = max(loan.remaining_months for loan in loans)
    
    # After prepayments
    adjusted_loans = []
    for loan in loans:
        alloc = next((a for a in allocations if a['loan_id'] == loan.id), None)
        if alloc:
            # Simulate prepayment
            sim = simulate_prepayment(loan.id, alloc['amount'], datetime.now().date(), 'reduce_tenure')
            adjusted_months = sim['reduce_tenure']['new_tenure_months']
        else:
            adjusted_months = loan.remaining_months
        adjusted_loans.append(adjusted_months)
    
    new_max_months = max(adjusted_loans)
    months_saved = original_max_months - new_max_months
    
    return months_saved
```

### Timeline Generation

```python
def generate_emi_timeline(
    loans: List[Loan],
    months: int = 24
) -> List[Dict]:
    """
    Generate month-by-month EMI breakdown for timeline chart.
    """
    timeline = []
    start_date = datetime.now().date().replace(day=1)
    
    for i in range(months):
        month_date = start_date + relativedelta(months=i)
        month_str = month_date.strftime('%Y-%m')
        
        breakdown = []
        total_emi = Decimal('0')
        
        for loan in loans:
            # Check if loan is still active in this month
            if is_loan_active_in_month(loan, month_date):
                breakdown.append({
                    'loan_id': str(loan.id),
                    'loan_name': loan.display_name or loan.name,
                    'emi': float(loan.emi_amount)
                })
                total_emi += loan.emi_amount
        
        timeline.append({
            'month': month_str,
            'total_emi': float(total_emi),
            'breakdown': breakdown
        })
    
    return timeline

def is_loan_active_in_month(loan: Loan, month_date: date) -> bool:
    """Check if loan has EMIs due in the given month."""
    # Get schedule entries for this loan in this month
    entries = db.query(LoanAmortizationSchedule).filter(
        LoanAmortizationSchedule.account_id == loan.id,
        extract('year', LoanAmortizationSchedule.due_date) == month_date.year,
        extract('month', LoanAmortizationSchedule.due_date) == month_date.month,
        LoanAmortizationSchedule.payment_status != 'paid'
    ).first()
    
    return entries is not None
```

## Implementation Phases

### Phase 1: Dashboard Summary (MVP) — Week 1

**Goal:** Dashboard page exists, shows KPIs and basic metrics

**Tasks:**
- [ ] Create `/loans/dashboard` route and page component
- [ ] Backend: `GET /api/v1/loans/dashboard/summary` endpoint
- [ ] Frontend: KPI cards (4 cards)
- [ ] Frontend: Upcoming payments table
- [ ] Update LoanDashboardWidget to link to full dashboard

**Deliverable:** User can navigate to dashboard, see summary metrics

### Phase 2: Debt Health Metrics — Week 2

**Goal:** DTI/FOIR calculation and display

**Tasks:**
- [ ] Backend: DTI/FOIR calculation logic
- [ ] Backend: `POST /api/v1/loans/dashboard/calculate-debt-health` endpoint
- [ ] Frontend: DebtHealthSection component with 2 gauges
- [ ] Frontend: Income/obligations input (inline edit)
- [ ] Store monthly_income in user preferences (optional)

**Deliverable:** User enters income, sees DTI/FOIR with color-coded status

### Phase 3: Strategy Simulator — Week 3

**Goal:** Compare prepayment strategies

**Tasks:**
- [ ] Backend: Avalanche, Snowball, Balanced algorithms
- [ ] Backend: `POST /api/v1/loans/dashboard/compare-strategies` endpoint
- [ ] Frontend: PrepaymentStrategySimulator component
- [ ] Frontend: 3 strategy cards with allocations breakdown
- [ ] Mark recommended strategy (highest savings)

**Deliverable:** User enters ₹2L, sees 3 strategies compared

### Phase 4: Timeline & Priority Ranking — Week 4

**Goal:** Visual timeline and priority tabs

**Tasks:**
- [ ] Backend: `GET /api/v1/loans/dashboard/timeline` endpoint
- [ ] Backend: `GET /api/v1/loans/dashboard/priority-ranking` endpoint
- [ ] Frontend: EMITimeline component (recharts BarChart)
- [ ] Frontend: PriorityRankingTabs component (3 tabs)
- [ ] Frontend: LoanCompositionPieChart

**Deliverable:** User sees month-by-month EMI chart, can compare priority orders

### Phase 5: Polish & Integration — Week 5

**Goal:** Complete UI, responsive, tested

**Tasks:**
- [ ] Mobile responsive layout (stack cards vertically)
- [ ] Loading states and error handling
- [ ] Empty states (no loans, no income data)
- [ ] Tooltips and help text
- [ ] Unit tests for calculation logic
- [ ] Integration tests for API endpoints
- [ ] Update LoanDashboardWidget to show debt health score

**Deliverable:** Production-ready dashboard

### Phase 6: Advanced Features (P1) — Future

- [ ] EMI calendar (month grid view)
- [ ] Historical trend charts (EMI paid over time)
- [ ] Goal integration (link loans to goals)
- [ ] What-if scenarios (increase EMI by X)
- [ ] Export dashboard as PDF report
- [ ] Refinance alerts (rate drop detection)

## UI/UX Considerations

### Responsive Design

**Desktop (≥1024px):**
- KPI cards: 4 columns
- Strategy cards: 3 columns side-by-side
- Timeline: full width, 24 months visible
- Priority tabs: side-by-side comparison

**Tablet (768-1023px):**
- KPI cards: 2 columns
- Strategy cards: 2 columns (Balanced wraps to next row)
- Timeline: scrollable horizontally
- Priority tabs: same as desktop

**Mobile (<768px):**
- KPI cards: 1 column, stacked
- Strategy cards: 1 column, swipeable carousel or tabs
- Timeline: scrollable, 6 months visible
- Priority tabs: accordion or full-screen tabs

### Color Palette (following shadcn/ui patterns)

**Loan Types:**
- Home Loan: `hsl(221, 83%, 53%)` (blue)
- Car Loan: `hsl(142, 71%, 45%)` (green)
- Personal Loan: `hsl(38, 92%, 50%)` (orange)
- Education Loan: `hsl(262, 83%, 58%)` (purple)
- Gold Loan: `hsl(43, 96%, 56%)` (yellow)
- Other: `hsl(215, 20%, 65%)` (gray)

**Health Status:**
- Healthy: `hsl(142, 71%, 45%)` (green-500)
- Moderate: `hsl(48, 96%, 53%)` (yellow-500)
- High Risk: `hsl(0, 72%, 51%)` (red-500)

**Strategy Cards:**
- Avalanche: Indigo accent
- Snowball: Teal accent
- Balanced: Violet accent
- Recommended badge: Gold/yellow shimmer

### Accessibility

- All gauges have aria-labels with current percentage
- Strategy cards keyboard navigable (Tab key)
- Color not sole indicator (use icons + text labels)
- High contrast mode support
- Screen reader announces "Recommended" badge

### Performance

**Optimization:**
- Lazy load timeline data (fetch next 12 months on scroll)
- Debounce strategy calculation (user stops typing amount)
- Cache dashboard summary for 5 minutes (stale-while-revalidate)
- Virtualize upcoming payments table if >100 rows

**Loading States:**
- Skeleton loaders for KPI cards during initial fetch
- Spinner on "Calculate Strategies" button
- Progressive rendering (show KPIs first, then charts)

## Testing Strategy

### Unit Tests

**Calculation Logic:**
```python
def test_dti_calculation():
    loans = [
        Loan(emi_amount=25000),
        Loan(emi_amount=12000),
        Loan(emi_amount=8000)
    ]
    dti = calculate_dti(loans, Decimal('130000'))
    assert dti == Decimal('34.62')  # (45000/130000)*100

def test_avalanche_strategy():
    loans = [
        Loan(id='1', current_balance=320000, interest_rate=9.5),
        Loan(id='2', current_balance=120000, interest_rate=8.2),
        Loan(id='3', current_balance=2800000, interest_rate=7.5)
    ]
    result = calculate_avalanche(loans, Decimal('200000'))
    assert result.allocations[0]['loan_id'] == '1'  # Highest rate first
    assert result.allocations[0]['amount'] == Decimal('200000')

def test_snowball_strategy():
    result = calculate_snowball(loans, Decimal('200000'))
    assert result.allocations[0]['loan_id'] == '2'  # Smallest balance first
    assert result.allocations[0]['amount'] == Decimal('120000')
    assert result.allocations[1]['amount'] == Decimal('80000')

def test_balanced_strategy():
    result = calculate_balanced(loans, Decimal('200000'))
    # Should close car loan (completable) then allocate to highest rate
    assert result.allocations[0]['loan_id'] == '2'
    assert result.allocations[0]['amount'] == Decimal('120000')
    assert result.allocations[1]['loan_id'] == '1'  # Highest rate
    assert result.loans_closed == 1
```

### Integration Tests

```python
def test_dashboard_summary_endpoint(client):
    response = client.get('/api/v1/loans/dashboard/summary')
    assert response.status_code == 200
    data = response.json()
    assert 'total_monthly_emi' in data
    assert 'debt_health' in data

def test_compare_strategies_endpoint(client):
    response = client.post(
        '/api/v1/loans/dashboard/compare-strategies',
        json={'prepayment_amount': 200000}
    )
    assert response.status_code == 200
    data = response.json()
    assert 'strategies' in data
    assert len(data['strategies']) == 3
    assert any(s['recommended'] for s in data['strategies'])
```

### Frontend Tests

```tsx
describe('PrepaymentStrategySimulator', () => {
  it('calculates strategies on button click', async () => {
    render(<PrepaymentStrategySimulator />)
    
    const amountInput = screen.getByLabelText(/prepayment amount/i)
    fireEvent.change(amountInput, { target: { value: '200000' } })
    
    const calculateButton = screen.getByRole('button', { name: /calculate/i })
    fireEvent.click(calculateButton)
    
    await waitFor(() => {
      expect(screen.getByText(/avalanche/i)).toBeInTheDocument()
      expect(screen.getByText(/snowball/i)).toBeInTheDocument()
      expect(screen.getByText(/balanced/i)).toBeInTheDocument()
    })
  })
  
  it('marks strategy with highest savings as recommended', async () => {
    // Mock API response
    mockFetch({
      strategies: [
        { name: 'avalanche', interest_saved: 345000, recommended: true },
        { name: 'snowball', interest_saved: 320000 },
        { name: 'balanced', interest_saved: 340000 }
      ]
    })
    
    render(<PrepaymentStrategySimulator />)
    // ... trigger calculation
    
    const avalancheCard = screen.getByText(/avalanche/i).closest('div')
    expect(within(avalancheCard).getByText(/recommended/i)).toBeInTheDocument()
  })
})
```

## Success Metrics

**Adoption:**
- % of users with loans who visit dashboard in first week
- Avg time spent on dashboard page

**Engagement:**
- % of users who use strategy simulator
- % of users who enter income (enabling DTI/FOIR)
- Avg strategies compared per user

**Value:**
- Prepayments made after using simulator (track via transactions)
- Interest saved (sum of all prepayments × rate difference)
- Loans closed after Snowball/Balanced recommendations

**Technical:**
- Dashboard page load time <2s (P95)
- Strategy calculation time <500ms (P95)
- Error rate <0.1% on API endpoints

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| User doesn't know monthly income | High | Allow skip, show "Enter income to see debt health" |
| Strategy calculation slow (many loans) | Medium | Optimize queries, cache schedule data, timeout at 5s |
| User expects live EMI tracking | Medium | Clarify this is planning tool, not payment tracker |
| Confusing strategy names | Medium | Add tooltips: "Avalanche = Math-based, Snowball = Psychology-based" |
| Mobile layout cramped | Low | Prioritize KPIs + upcoming payments, collapse other sections |

## Dependencies

**Existing Securo Features:**
- Loan accounts (type='loan') ✅
- Amortization schedules ✅
- LoanSimulations component (prepayment simulation) ✅
- Transaction system ✅

**External Libraries:**
- recharts (charts) — already used in project ✅
- date-fns (date manipulation) — already used ✅
- shadcn/ui components (Card, Tabs, Badge, etc.) ✅

**New Backend Dependencies:**
- None (pure Python/SQLAlchemy logic)

## Open Questions

1. **Income storage:** Should monthly_income be user-level or workspace-level?
   - **Decision:** Workspace-level (business users may have team income, personal users have household income)

2. **Strategy recommendation:** Always show all 3, or only show Avalanche + Balanced?
   - **Decision:** Show all 3. Users deserve to see the psychology-based option even if it's not optimal.

3. **Completable threshold:** In Balanced strategy, what if prepayment is 95% of loan balance?
   - **Decision:** "Completable" means `prepayment >= balance`. User can top up last ₹5k manually.

4. **Timeline projection:** Show with or without projected prepayments?
   - **Decision:** Without (baseline). Phase 2 can add toggle "Show with planned prepayment".

5. **Debt health:** DTI or FOIR as primary metric?
   - **Decision:** Show both. DTI for US-aligned users, FOIR for Indian context.

## Competitor Comparison Matrix

| Feature | ET Money | BankBazaar | Paisabazaar | Securo (Proposed) |
|---------|----------|------------|-------------|-------------------|
| EMI calendar | ✅ Full | ❌ | ❌ | ✅ (P1) |
| Prepayment calc | ✅ Basic | ✅ Advanced | ❌ | ✅ 3 strategies |
| Strategy comparison | ❌ | ❌ | ❌ | ✅ Unique |
| DTI calculation | ❌ | ❌ | ✅ | ✅ |
| FOIR calculation | ❌ | ✅ | ✅ | ✅ Both |
| Timeline view | ❌ | ❌ | ❌ | ✅ Unique |
| Priority ranking | ❌ | ❌ | ❌ | ✅ Unique |
| Smart allocation | ❌ | ❌ | ❌ | ✅ Unique |
| Balance transfer | ❌ | ✅ Marketplace | ✅ | ❌ (P2) |
| Self-hosted | ❌ | ❌ | ❌ | ✅ |

**Securo's differentiators:**
1. Only app with **3-strategy comparison** (Avalanche, Snowball, Balanced)
2. Only app with **visual priority ranking** across strategies
3. Only app with **timeline projection** (debt-free date visualization)
4. Only **self-hosted** solution (privacy-first)

## Appendix: Balanced Strategy Rationale

**Why Balanced strategy exists:**

Purely mathematical (Avalanche) is optimal for interest savings, but humans aren't robots. Behavioral economics research (Dan Ariely, Richard Thaler) shows:

1. **Small wins matter:** Closing a loan (even small) gives motivation boost
2. **Decision fatigue:** Fewer active loans = less mental overhead
3. **Cashflow flexibility:** Closing smallest loan frees up that EMI for emergencies

**Balanced strategy logic:**
- Phase 1: Close any loans where `prepayment >= balance` (instant win)
- Phase 2: Allocate remainder to highest interest rate (math kicks in)

**Example:**
- Prepayment: ₹2L
- Car loan: ₹1.2L @ 8.2% (completable)
- Personal loan: ₹3.2L @ 9.5% (highest rate)
- Home loan: ₹28L @ 7.5%

**Avalanche:** ₹2L → Personal loan (9.5% highest)  
**Snowball:** ₹1.2L → Car (close it), ₹80k → Personal  
**Balanced:** ₹1.2L → Car (close it), ₹80k → Personal (highest rate)  

Result: Balanced = Snowball in this case, but differs when multiple loans are completable.

**When Balanced wins over Avalanche:**
- User has 2+ small loans completable with prepayment
- Closing them frees up EMI for next prepayment cycle
- Compounds into faster debt freedom than pure Avalanche

**When Avalanche still wins:**
- No loans are completable with prepayment amount
- Highest rate loan is also smallest (Avalanche = Snowball)
- User is purely math-focused, doesn't care about loan count

**UI Communication:**
- Avalanche card: "Math-based: Maximum interest savings"
- Snowball card: "Psychology-based: Quick wins, motivation"
- Balanced card: "Hybrid: Close completable loans, then highest interest"

---

**Status:** Ready for review  
**Next step:** User approval → create implementation plan
