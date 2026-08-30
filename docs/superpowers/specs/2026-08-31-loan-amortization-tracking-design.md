# Loan Amortization Tracking Design

**Date:** 2026-08-31  
**Status:** Draft  
**Author:** AI Assistant

## Overview

Add comprehensive loan amortization tracking with EMI-level payment breakdowns, automatic transaction linking, prepayment handling, and detailed analytics including yearly principal vs interest summaries and debt ratios.

## Goals

- Generate full amortization schedules automatically when loans are created
- Break down each EMI into principal and interest components
- Auto-link loan account transactions to scheduled payments
- Handle prepayments with user-chosen recalculation (reduce EMI vs reduce tenure)
- Provide detailed analytics: yearly summaries, debt ratios, payoff projections
- Enable editing of schedule entries and loan parameters
- Display dashboard widget with aggregate loan metrics

## Non-Goals

- Integration with external loan providers or banks
- Automated payment reminders via email/SMS (future enhancement)
- Multi-currency loan calculations (use existing FX system)
- Complex loan types (balloon payments, adjustable rates) in initial version

## Architecture

### Database Schema

**New Tables:**

1. **loan_amortization_schedules**
   - `id`: UUID (PK)
   - `account_id`: UUID (FK → accounts)
   - `workspace_id`: UUID (FK → workspaces)
   - `schedule_version`: INTEGER (incremented on recalculation)
   - `emi_number`: INTEGER (1-indexed installment number)
   - `due_date`: DATE
   - `principal_component`: NUMERIC(15,2)
   - `interest_component`: NUMERIC(15,2)
   - `emi_amount`: NUMERIC(15,2)
   - `opening_balance`: NUMERIC(15,2)
   - `closing_balance`: NUMERIC(15,2)
   - `payment_status`: VARCHAR(20) (scheduled, paid, partial, missed, skipped)
   - `actual_payment_date`: DATE (nullable)
   - `actual_amount_paid`: NUMERIC(15,2) (nullable)
   - `linked_transaction_id`: UUID (nullable, FK → transactions)
   - `notes`: TEXT (nullable)
   - `created_at`: TIMESTAMP
   - `updated_at`: TIMESTAMP
   - Indexes: `account_id`, `due_date`, `payment_status`, `schedule_version`
   - Unique: `(account_id, schedule_version, emi_number)`

2. **loan_prepayments**
   - `id`: UUID (PK)
   - `account_id`: UUID (FK → accounts)
   - `workspace_id`: UUID (FK → workspaces)
   - `transaction_id`: UUID (FK → transactions, nullable)
   - `prepayment_amount`: NUMERIC(15,2)
   - `prepayment_date`: DATE
   - `recalculation_method`: VARCHAR(20) (reduce_emi, reduce_tenure)
   - `schedule_version_before`: INTEGER
   - `schedule_version_after`: INTEGER
   - `tenure_change_months`: INTEGER (nullable)
   - `emi_change_amount`: NUMERIC(15,2) (nullable)
   - `created_at`: TIMESTAMP
   - Indexes: `account_id`, `prepayment_date`

**Updates to Existing Tables:**

`accounts` table additions:
- `current_schedule_version`: INTEGER (default 1)
- `last_payment_date`: DATE (nullable)
- `total_prepayments`: NUMERIC(15,2) (default 0)

### Backend Services

**LoanScheduleService** (`app/services/loan_schedule_service.py`)
- `generate_amortization_schedule(account_id, version)`: Create full schedule using reducing balance method
- `regenerate_schedule(account_id, from_emi_number, new_params)`: Recalculate from specific EMI onwards
- `calculate_emi(principal, rate, tenure)`: Standard EMI calculation formula
- `get_schedule(account_id, version, filters)`: Retrieve schedule with filtering
- `update_schedule_entry(entry_id, updates)`: Edit individual schedule entries
- `bulk_update_dates(account_id, shift_days, new_emi_day, from_emi)`: Bulk date modifications

**LoanPaymentService** (`app/services/loan_payment_service.py`)
- `auto_link_transactions(account_id, date_tolerance, amount_tolerance)`: Find and link matching transactions
- `link_transaction_to_entry(entry_id, transaction_id)`: Manual linking
- `mark_payment_status(entry_id, status, actual_date, actual_amount)`: Update payment status
- `record_prepayment(account_id, amount, date, method, transaction_id)`: Process prepayment and trigger recalculation
- `simulate_prepayment(account_id, amount, date)`: Calculate both recalculation options without applying

**LoanAnalyticsService** (`app/services/loan_analytics_service.py`)
- `get_loan_overview(account_id)`: Summary metrics (outstanding, paid, progress)
- `get_yearly_breakdown(account_id, group_by)`: Principal vs interest by period
- `get_payment_summary(account_id, period)`: Payment history statistics
- `calculate_debt_ratios(loan_ids, monthly_income)`: DTI, EMI-to-income ratios
- `get_chart_data(account_id, chart_type)`: Data for visualizations
- `get_dashboard_summary(workspace_id)`: Aggregate metrics for widget

### API Endpoints

**Loan Management:**
- `POST /api/loans` - Create loan with schedule generation
- `PATCH /api/loans/{loan_id}` - Update loan parameters
- `POST /api/loans/{loan_id}/close` - Close/archive loan
- `GET /api/loans` - List all loans with summary

**Schedule Operations:**
- `GET /api/loans/{loan_id}/schedule` - Get full amortization schedule
- `PATCH /api/loans/schedule/{entry_id}` - Update schedule entry
- `PATCH /api/loans/{loan_id}/schedule/bulk-update-dates` - Bulk date changes
- `POST /api/loans/schedule/{entry_id}/mark-status` - Mark EMI status
- `POST /api/loans/{loan_id}/schedule/regenerate` - Regenerate from EMI number
- `GET /api/loans/{loan_id}/schedule/export` - Export schedule (CSV/PDF)

**Prepayments:**
- `POST /api/loans/{loan_id}/prepayments` - Record prepayment with recalculation
- `GET /api/loans/{loan_id}/prepayments` - Prepayment history
- `POST /api/loans/{loan_id}/prepayments/simulate` - Simulate prepayment options

**Transaction Linking:**
- `POST /api/loans/{loan_id}/link-transactions` - Auto-link transactions
- `POST /api/loans/schedule/{entry_id}/link-transaction` - Manual link
- `DELETE /api/loans/schedule/{entry_id}/unlink-transaction` - Unlink

**Analytics:**
- `GET /api/loans/{loan_id}/analytics` - Comprehensive loan analytics
- `GET /api/loans/{loan_id}/analytics/yearly-breakdown` - Yearly principal vs interest
- `GET /api/loans/analytics/debt-ratios` - Debt ratios across loans
- `GET /api/loans/{loan_id}/analytics/chart-data` - Chart data for visualizations
- `GET /api/dashboard/loans-summary` - Dashboard widget data

**Bulk & Events:**
- `POST /api/loans/bulk-import-payments` - Bulk payment import
- `GET /api/loans/events` - Event stream for agent integration
- `POST /api/loans/process-scheduled-actions` - Process scheduled tasks

### Frontend Components

**Dashboard Widget** (`components/loans-summary-widget.tsx`)
- Total outstanding across all loans
- Total monthly EMI
- Next 5 upcoming payments
- Recent 5 payments
- YTD principal vs interest totals
- Payment alerts (due, overdue)

**Detailed Loan View** (`pages/loan-detail.tsx`)
- Loan summary card (outstanding, progress, next EMI)
- Full amortization schedule table with filters
- Yearly breakdown chart (principal vs interest stacked bars)
- Payment history timeline
- Prepayment dialog with simulation
- Edit schedule entry modal
- Export options

**Amortization Schedule Table** (`components/amortization-schedule-table.tsx`)
- Columns: EMI #, Due Date, Principal, Interest, Total EMI, Balance, Status, Actions
- Sortable and filterable
- Row actions: Mark paid/missed, Link transaction, Edit, Add note
- Color-coded status indicators
- Inline editing for dates and amounts

**Prepayment Dialog** (`components/prepayment-dialog.tsx`)
- Amount input
- Date picker
- Simulation results for both options (reduce EMI vs reduce tenure)
- Side-by-side comparison: savings, new schedule preview
- Method selection and confirmation

**Analytics Dashboard** (`components/loan-analytics.tsx`)
- Key metrics cards
- Balance trajectory chart (projected vs actual)
- Principal vs interest distribution (pie/donut)
- Yearly breakdown chart (stacked bar)
- Payment history table
- Debt ratio indicators with thresholds

## Data Flow

### Loan Creation Flow
1. User creates loan via POST /api/loans with required fields
2. Backend creates account record with type="loan"
3. LoanScheduleService.generate_amortization_schedule() called
4. Schedule entries created for full tenure using reducing balance method
5. Each entry stores principal/interest breakdown, opening/closing balance
6. Response includes schedule summary and first/last EMI dates

### Transaction Linking Flow
1. User creates transaction on loan account (regular transaction flow)
2. Background job or manual trigger calls auto_link_transactions()
3. Service matches transaction to schedule entry by date (±tolerance) and amount (±%)
4. If match found with high confidence, auto-link; otherwise mark for review
5. Schedule entry updated with linked_transaction_id, payment_status="paid"
6. Actual payment date and amount recorded

### Prepayment Flow
1. User clicks "Record Prepayment" in loan detail view
2. Enters amount and date, clicks "Simulate"
3. Frontend calls POST /api/loans/{id}/prepayments/simulate
4. Backend calculates both options (reduce EMI vs reduce tenure)
5. Returns new EMI/tenure, interest saved, sample schedule for each
6. User selects preferred method and confirms
7. Backend creates prepayment record, increments schedule_version
8. Regenerates schedule from next EMI onwards with new parameters
9. Old schedule entries remain (archived by version number)

### Schedule Editing Flow
1. User edits schedule entry (date, amount, or breakdown)
2. Frontend calls PATCH /api/loans/schedule/{entry_id}
3. Service updates entry and checks if recalculation needed
4. If principal/interest changed, subsequent entries recalculated
5. Returns affected entry count for user confirmation

## Calculations

### EMI Calculation (Reducing Balance)
```
EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)

Where:
P = Principal amount
r = Monthly interest rate (annual_rate / 12 / 100)
n = Tenure in months
```

### Schedule Generation Algorithm
```
For each month i from 1 to tenure:
  opening_balance = remaining_principal
  interest_component = opening_balance × monthly_rate
  principal_component = emi_amount - interest_component
  closing_balance = opening_balance - principal_component
  
  Create schedule entry with:
    - emi_number = i
    - due_date = disbursed_on + i months (adjusted to emi_day)
    - principal_component, interest_component, emi_amount
    - opening_balance, closing_balance
    - payment_status = "scheduled"
```

### Prepayment Recalculation

**Reduce EMI Option:**
```
new_principal = current_outstanding - prepayment_amount
remaining_months = original_tenure - elapsed_months
new_emi = calculate_emi(new_principal, rate, remaining_months)
```

**Reduce Tenure Option:**
```
new_principal = current_outstanding - prepayment_amount
keep emi_amount = original_emi
new_tenure = calculate_tenure(new_principal, rate, emi_amount)
months_saved = remaining_months - new_tenure
```

## Analytics Metrics

### Loan Overview
- Original principal, current outstanding, principal paid
- Interest paid, total paid
- Progress percentage: (principal_paid / original_principal) × 100
- EMIs paid vs remaining

### Payment Summary
- On-time, late, missed payment counts
- Average days late
- Prepayment count and total

### Financial Metrics
- Total interest payable (sum of all interest components)
- Interest saved from prepayments
- Forecasted vs original payoff date
- Effective interest rate (actual interest paid / principal)

### Debt Ratios
- **DTI (Debt-to-Income):** total_monthly_emi / monthly_income
- **EMI-to-Income:** aggregate_emi / monthly_income
- **LTV (Loan-to-Value):** loan_balance / asset_value (if linked asset exists)
- Thresholds: DTI < 36% (healthy), EMI < 40% (healthy)

### Yearly Breakdown
- Group schedule entries by year
- Sum principal_component, interest_component per year
- Include actual payments (from linked transactions)
- Show prepayments separately
- Calculate year-end closing balance

## Error Handling

- **Invalid loan parameters:** Validate principal > 0, rate > 0, tenure > 0 before schedule generation
- **Schedule version conflicts:** Use optimistic locking, reject edits on stale versions
- **Transaction linking ambiguity:** When multiple entries match, flag for manual review
- **Prepayment > outstanding:** Reject with error; prepayment cannot exceed current balance
- **Missing EMI date:** If account doesn't have emi_day, default to disbursed_on day-of-month
- **Schedule regeneration failures:** Rollback to previous version, surface error to user

## Security & Permissions

- All endpoints scoped to workspace_id (multi-tenancy)
- Only workspace members with write permissions can modify loans/schedules
- Read-only users can view schedules and analytics
- Prepayment records immutable once created (audit trail)
- Schedule version history preserved (never deleted)

## Testing Strategy

### Unit Tests
- EMI calculation accuracy (compare to known values)
- Schedule generation correctness (reducing balance validation)
- Prepayment recalculation (both methods, edge cases)
- Transaction auto-linking logic (tolerance matching)
- Debt ratio calculations

### Integration Tests
- Full loan lifecycle: create → generate schedule → link transactions → prepayment → close
- API endpoint coverage for all operations
- Database constraints (unique, foreign keys, cascades)
- Multi-currency handling via existing FX system

### Edge Cases
- Loan with 1 month tenure
- Prepayment on last EMI
- Multiple prepayments in same month
- Editing paid EMI entry (should warn or restrict)
- Closing loan with outstanding balance
- Schedule regeneration from EMI #1 vs mid-tenure

## Migration Plan

1. **Alembic Migration 078:** Create loan_amortization_schedules and loan_prepayments tables, add columns to accounts
2. **Backfill existing loans:** Run script to generate schedules for existing loan accounts (if any)
3. **Deploy backend services:** LoanScheduleService, LoanPaymentService, LoanAnalyticsService
4. **Deploy API endpoints:** All 24 endpoints, versioned as /api/v1/loans
5. **Deploy frontend components:** Dashboard widget, detailed view, dialogs
6. **Background job:** Setup periodic task for auto-linking transactions (daily)
7. **Monitoring:** Add metrics for schedule generation time, linking accuracy

## Future Enhancements

- Automated payment reminders (email/SMS/push)
- Variable interest rate loans with rate change history
- Grace period and penalty charge tracking
- Loan refinancing workflow
- Loan comparison tool (different rates/tenures)
- Integration with goal tracking (pay off by date)
- Bulk loan import from CSV
- Loan statements/reports generation
- Amortization schedule PDF export with branding

## Dependencies

- Existing account management system
- Transaction system for linking
- FX rate system for multi-currency
- Dashboard framework for widget
- Chart library (recharts or similar) for visualizations
- PDF generation library for exports

## Success Metrics

- 100% of new loans auto-generate schedules within 2 seconds
- >90% transaction auto-linking accuracy (date ±5 days, amount ±2%)
- Prepayment simulation response time < 500ms
- Dashboard widget load time < 1 second
- User can edit schedule entry and see updated calculations within 3 seconds

## Open Questions

None - all requirements clarified during brainstorming.
