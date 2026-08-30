# Loan Amortization Feature

A comprehensive loan management and amortization tracking system for SecureFinanceApp.

## Features

### Core Functionality

- **Amortization Schedule Management**: Generate, view, and manage complete loan schedules with EMI breakdowns
- **Prepayment Simulation & Recording**: Compare reduce-EMI vs reduce-tenure options with interest savings calculations
- **Transaction Auto-Linking**: Automatically match loan payments to schedule entries with confidence scoring
- **Schedule Versioning**: Track schedule changes over time with full audit trail
- **Bulk Operations**: Manage multiple loans and schedule entries efficiently

### Analytics & Insights

- **Loan Overview**: Track progress, principal/interest paid vs remaining, prepayment totals
- **Payment Breakdown**: Analyze payments by year, quarter, or month
- **Debt Health Metrics**: Calculate debt-to-income ratios and financial health status
- **Dashboard**: Monitor upcoming payments, recent activity, and alerts

### Utilities

- **EMI Calculator**: Calculate monthly payment for any loan parameters
- **Prepayment Savings Calculator**: Estimate interest savings before prepaying
- **Schedule Validation**: Verify schedule integrity after manual edits
- **CSV Export**: Export single or multiple loan schedules
- **Workspace Summary**: Aggregate view of all loans

## Architecture

### Backend (Python/FastAPI)

- **Models**: `LoanAmortizationSchedule`, `LoanPrepayment` with SQLAlchemy
- **Services**: Business logic for schedule generation, prepayment calculations, linking
- **API Routes**: RESTful endpoints under `/api/v1/loans` and `/api/v1/schedule`
- **Database**: PostgreSQL with Alembic migrations

### Frontend (React/TypeScript)

- **Components**: `LoanDashboardWidget`, `LoanDetailPage`, `LoanScheduleTable`, `PrepaymentDialog`
- **State Management**: TanStack Query for server state
- **UI Library**: shadcn/ui components

## API Endpoints

### Schedule Management
- `GET /loans/{id}/schedule` - Retrieve schedule with filters
- `GET /loans/{id}/schedule/export` - Export as CSV
- `PATCH /schedule/{entry_id}` - Update single entry
- `POST /schedule/bulk-update-dates` - Bulk date updates
- `PUT /schedule/{entry_id}/status` - Mark payment status
- `POST /schedule/regenerate` - Regenerate from EMI number

### Prepayments
- `POST /prepayments/simulate` - Compare prepayment options
- `POST /prepayments` - Record prepayment and regenerate
- `GET /loans/{id}/prepayments` - List prepayment history

### Transaction Linking
- `POST /schedule/auto-link` - Auto-link with confidence scoring
- `POST /schedule/{entry_id}/link` - Manual linking

### Analytics
- `GET /loans/{id}/overview` - Progress and breakdown metrics
- `GET /loans/{id}/breakdown` - Yearly/quarterly/monthly analysis
- `GET /loans/debt-ratios` - Financial health metrics
- `GET /loans/dashboard` - Summary with alerts

### Bulk Operations
- `POST /schedule/bulk-mark-status` - Batch status updates
- `POST /schedule/bulk-delete` - Cleanup/reset versions
- `POST /schedule/bulk-export` - ZIP export

### Utilities
- `POST /loans/calculate-emi` - EMI calculation
- `POST /loans/validate-schedule` - Integrity checks
- `GET /loans/summary` - Workspace summary
- `POST /loans/calculate-savings` - Prepayment savings

## Database Schema

### LoanAmortizationSchedule

```sql
CREATE TABLE loan_amortization_schedule (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    account_id UUID NOT NULL,
    schedule_version INTEGER NOT NULL,
    emi_number INTEGER NOT NULL,
    due_date DATE NOT NULL,
    principal_component DECIMAL(15,2) NOT NULL,
    interest_component DECIMAL(15,2) NOT NULL,
    emi_amount DECIMAL(15,2) NOT NULL,
    opening_balance DECIMAL(15,2) NOT NULL,
    closing_balance DECIMAL(15,2) NOT NULL,
    payment_status VARCHAR(20) NOT NULL,
    linked_transaction_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### LoanPrepayment

```sql
CREATE TABLE loan_prepayment (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    account_id UUID NOT NULL,
    prepayment_amount DECIMAL(15,2) NOT NULL,
    prepayment_date DATE NOT NULL,
    recalculation_method VARCHAR(20) NOT NULL,
    schedule_version_before INTEGER NOT NULL,
    schedule_version_after INTEGER NOT NULL,
    emi_change_amount DECIMAL(15,2),
    tenure_change_months INTEGER,
    interest_saved DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Usage Examples

### Generate Amortization Schedule

```python
entries = await loan_schedule_service.regenerate_schedule(
    db=db,
    account_id=account_id,
    workspace_id=workspace_id,
    from_emi_number=1,
    new_principal=Decimal("1000000.00"),
    new_annual_rate=Decimal("8.5"),
    new_tenure_months=240,
    start_date=date(2026, 1, 1),
)
```

### Simulate Prepayment

```python
simulation = await loan_payment_service.simulate_prepayment(
    db=db,
    account_id=account_id,
    workspace_id=workspace_id,
    prepayment_amount=Decimal("100000.00"),
    annual_interest_rate=Decimal("8.5"),
    current_emi_number=12,
)
# Returns: {'reduce_emi': {...}, 'reduce_tenure': {...}}
```

### Auto-Link Transactions

```python
matches = await loan_payment_service.auto_link_transactions(
    db=db,
    account_id=account_id,
    workspace_id=workspace_id,
    date_tolerance_days=3,
    amount_tolerance_percent=Decimal("2.0"),
)
# Returns: [{'schedule_entry_id': ..., 'transaction_id': ..., 'confidence': 'exact'}]
```

### Frontend: Display Dashboard Widget

```tsx
import { LoanDashboardWidget } from '@/components/loans/LoanDashboardWidget';

function Dashboard() {
  return (
    <div className="grid grid-cols-3 gap-4">
      <LoanDashboardWidget />
      {/* Other widgets */}
    </div>
  );
}
```

## Testing

### Backend Tests

- **Unit Tests**: Service layer logic, EMI calculations, validation
- **API Tests**: Route handlers for all endpoints
- **Integration Tests**: End-to-end loan lifecycle workflows

Run tests:
```bash
cd backend
pytest tests/test_loan_*.py -v
```

### Frontend Tests

- **Component Tests**: Widget rendering, user interactions
- **Integration Tests**: Data fetching, state updates

Run tests:
```bash
cd frontend
npm test -- loans
```

## Installation & Setup

### Backend

1. Run database migration:
```bash
cd backend
alembic upgrade head
```

2. The loan models and routes are automatically included in the FastAPI app.

### Frontend

1. Import and use components:
```tsx
import { LoanDashboardWidget } from '@/components/loans/LoanDashboardWidget';
import { LoanDetailPage } from '@/pages/loans/LoanDetailPage';
```

2. Add routes:
```tsx
<Route path="/loans/:accountId" element={<LoanDetailPage />} />
```

## Configuration

### Schedule Generation

- **Default EMI Calculation Method**: Reducing balance (standard amortization)
- **Decimal Precision**: 2 decimal places for currency amounts
- **Version History**: Unlimited versions retained

### Auto-Linking

- **Default Date Tolerance**: 3 days
- **Default Amount Tolerance**: 2%
- **Confidence Thresholds**:
  - Exact: Same date AND same amount
  - High: Within date tolerance AND exact amount
  - Medium: Within both tolerances
  - Low: Outside tolerances but flagged for review

### Analytics

- **Dashboard Refresh**: 5 minutes
- **Upcoming Payment Window**: 7 days
- **Debt Health Status**:
  - Healthy: DTI < 40%
  - Moderate: DTI 40-60%
  - High Risk: DTI > 60%

## Performance Considerations

- **Bulk Operations**: Use bulk endpoints for operations on >10 entries
- **Schedule Versioning**: Old versions are retained but not loaded by default
- **Query Optimization**: Indexes on `account_id`, `schedule_version`, `due_date`
- **CSV Export**: Streaming response for large schedules
- **Frontend Caching**: TanStack Query caches API responses

## Security

- **Workspace Isolation**: All queries filtered by `workspace_id`
- **Authentication**: Bearer token required for all endpoints
- **Authorization**: `require_workspace_access` dependency enforces permissions
- **Input Validation**: Pydantic schemas validate all inputs
- **SQL Injection**: SQLAlchemy ORM prevents injection attacks

## Limitations

- **Currency**: Each loan is single-currency; no multi-currency schedules
- **Interest Rate**: Fixed rate per schedule version; use regenerate for rate changes
- **EMI Day**: Must be between 1-28 for reliable monthly recurrence
- **Schedule Size**: Tested up to 360 entries (30-year loans)

## Future Enhancements

- [ ] Variable interest rate schedules
- [ ] Custom amortization methods (bullet, balloon)
- [ ] Schedule import from external sources
- [ ] Mobile app notifications for due payments
- [ ] Integration with bank feeds for auto-payment detection
- [ ] Prepayment optimization recommendations
- [ ] Multi-currency loan support
- [ ] Loan comparison tool

## Documentation

- [API Documentation](../docs/api/loan-amortization.md)
- [User Guide](../docs/user-guide/loan-amortization.md)
- [Database Schema](../backend/alembic/versions/077_loan_and_sip_fields.py)

## Contributing

See the main repository [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

Part of SecureFinanceApp - see main [LICENSE](../../LICENSE) file.
