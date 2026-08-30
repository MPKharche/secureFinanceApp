# Loan Amortization API Documentation

This document describes the API endpoints for the loan amortization feature.

## Base URL

All endpoints are prefixed with `/api/v1`

## Authentication

All endpoints require authentication via Bearer token:

```
Authorization: Bearer <token>
```

## Endpoints

### Schedule Management

#### Get Loan Schedule

```
GET /loans/{account_id}/schedule
```

Retrieve the amortization schedule for a loan account.

**Query Parameters:**
- `status` (optional): Filter by payment status (`scheduled`, `paid`, `partial`, `missed`, `skipped`)
- `from_date` (optional): Filter entries from this date (ISO 8601 format)
- `to_date` (optional): Filter entries up to this date (ISO 8601 format)

**Response:**
```json
[
  {
    "id": "uuid",
    "emi_number": 1,
    "due_date": "2026-09-01",
    "principal_component": "2000.00",
    "interest_component": "1000.00",
    "emi_amount": "3000.00",
    "opening_balance": "100000.00",
    "closing_balance": "98000.00",
    "payment_status": "scheduled"
  }
]
```

#### Export Schedule as CSV

```
GET /loans/{account_id}/schedule/export
```

Export the loan schedule as a CSV file.

**Response:** CSV file download

#### Update Schedule Entry

```
PATCH /schedule/{entry_id}
```

Update a single schedule entry.

**Request Body:**
```json
{
  "due_date": "2026-09-05",
  "emi_amount": "3500.00"
}
```

**Response:** Updated schedule entry object

#### Bulk Update Dates

```
POST /schedule/bulk-update-dates
```

Bulk update due dates for multiple schedule entries.

**Request Body:**
```json
{
  "account_id": "uuid",
  "from_emi_number": 5,
  "shift_days": 7,
  "new_day_of_month": 15
}
```

Either `shift_days` or `new_day_of_month` should be provided (not both).

**Response:**
```json
{
  "updated_count": 10
}
```

#### Mark Payment Status

```
PUT /schedule/{entry_id}/status
```

Mark a schedule entry's payment status.

**Request Body:**
```json
{
  "payment_status": "paid"
}
```

**Response:** Updated schedule entry object

#### Regenerate Schedule

```
POST /schedule/regenerate
```

Regenerate the loan schedule from a specific EMI number with new parameters.

**Request Body:**
```json
{
  "account_id": "uuid",
  "from_emi_number": 6,
  "new_principal": "60000.00",
  "new_annual_rate": "8.5",
  "new_tenure_months": 10,
  "start_date": "2027-03-01"
}
```

**Response:**
```json
{
  "new_schedule_version": 2,
  "entries_created": 10
}
```

### Prepayments

#### Simulate Prepayment

```
POST /prepayments/simulate
```

Simulate prepayment options (reduce EMI vs reduce tenure).

**Request Body:**
```json
{
  "account_id": "uuid",
  "prepayment_amount": "50000.00",
  "annual_interest_rate": "9.0",
  "current_emi_number": 10
}
```

**Response:**
```json
{
  "reduce_emi": {
    "new_emi_amount": "7500.00",
    "new_tenure_months": 24,
    "total_interest_saved": "15000.00"
  },
  "reduce_tenure": {
    "new_emi_amount": "9000.00",
    "new_tenure_months": 18,
    "total_interest_saved": "20000.00"
  }
}
```

#### Record Prepayment

```
POST /prepayments
```

Record a prepayment and regenerate the schedule.

**Request Body:**
```json
{
  "account_id": "uuid",
  "prepayment_amount": "50000.00",
  "annual_interest_rate": "9.0",
  "current_emi_number": 10,
  "recalculation_method": "reduce_tenure"
}
```

**Response:**
```json
{
  "id": "uuid",
  "account_id": "uuid",
  "prepayment_amount": "50000.00",
  "recalculation_method": "reduce_tenure",
  "schedule_version_before": 1,
  "schedule_version_after": 2,
  "emi_change_amount": "0.00",
  "tenure_change_months": -6,
  "created_at": "2026-08-25T10:00:00Z"
}
```

#### List Prepayments

```
GET /loans/{account_id}/prepayments
```

List prepayment history for a loan account.

**Response:** Array of prepayment objects

### Transaction Linking

#### Auto-Link Transactions

```
POST /schedule/auto-link
```

Automatically link transactions to schedule entries with confidence scoring.

**Request Body:**
```json
{
  "account_id": "uuid",
  "date_tolerance_days": 3,
  "amount_tolerance_percent": "2.0"
}
```

**Response:**
```json
{
  "linked_count": 5,
  "matches": [
    {
      "schedule_entry_id": "uuid",
      "transaction_id": "uuid",
      "confidence": "exact"
    }
  ]
}
```

Confidence levels: `exact`, `high`, `medium`, `low`

#### Manual Link Transaction

```
POST /schedule/{entry_id}/link
```

Manually link a transaction to a schedule entry.

**Request Body:**
```json
{
  "transaction_id": "uuid"
}
```

**Response:** Updated schedule entry object

### Analytics

#### Get Loan Overview

```
GET /loans/{account_id}/overview
```

Get loan overview metrics.

**Response:**
```json
{
  "progress_percent": 25.5,
  "emis_paid": 6,
  "emis_remaining": 18,
  "principal_paid": "120000.00",
  "principal_remaining": "480000.00",
  "interest_paid": "45000.00",
  "interest_remaining": "135000.00",
  "total_prepayments": "20000.00"
}
```

#### Get Payment Breakdown

```
GET /loans/{account_id}/breakdown?group_by={period}
```

Get yearly/quarterly/monthly breakdown of payments.

**Query Parameters:**
- `group_by`: `year`, `quarter`, or `month`

**Response:**
```json
[
  {
    "period": "2026",
    "principal_paid": "50000.00",
    "interest_paid": "25000.00",
    "total_paid": "75000.00",
    "prepayments": "10000.00"
  }
]
```

#### Calculate Debt Ratios

```
GET /loans/debt-ratios?monthly_income={amount}
```

Calculate debt-to-income and other financial ratios.

**Query Parameters:**
- `monthly_income` (optional): Monthly income for ratio calculation

**Response:**
```json
{
  "total_monthly_emi": "45000.00",
  "debt_to_income_ratio": "0.45",
  "emi_to_income_ratio": "0.45",
  "total_outstanding": "500000.00",
  "weighted_avg_interest_rate": "8.75",
  "health_status": "healthy"
}
```

Health status: `healthy`, `moderate`, `high_risk`

#### Get Dashboard Summary

```
GET /loans/dashboard
```

Get dashboard summary with next payments, recent activity, and alerts.

**Response:**
```json
{
  "next_due_payments": [
    {
      "account_id": "uuid",
      "account_name": "Home Loan",
      "due_date": "2026-09-05",
      "emi_amount": "25000.00",
      "days_until_due": 5
    }
  ],
  "recent_payments": [
    {
      "account_name": "Car Loan",
      "payment_date": "2026-08-25",
      "amount_paid": "15000.00"
    }
  ],
  "alerts": [
    {
      "type": "payment_due",
      "message": "Payment due in 3 days",
      "account_id": "uuid"
    }
  ],
  "total_monthly_emi": "40000.00",
  "total_outstanding": "500000.00"
}
```

### Bulk Operations

#### Bulk Mark Status

```
POST /schedule/bulk-mark-status
```

Bulk mark payment status for multiple schedule entries.

**Request Body:**
```json
{
  "entry_ids": ["uuid1", "uuid2", "uuid3"],
  "payment_status": "paid"
}
```

**Response:**
```json
{
  "updated_count": 3
}
```

#### Bulk Delete Schedules

```
POST /schedule/bulk-delete
```

Bulk delete schedule entries for specific accounts and version.

**Request Body:**
```json
{
  "account_ids": ["uuid1", "uuid2"],
  "schedule_version": 1
}
```

**Response:**
```json
{
  "deleted_count": 24
}
```

#### Bulk Export Schedules

```
POST /schedule/bulk-export
```

Bulk export schedules for multiple loans as a ZIP file.

**Request Body:**
```json
{
  "account_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response:** ZIP file download containing CSV files for each loan

### Utilities

#### Calculate EMI

```
POST /loans/calculate-emi
```

Calculate EMI for given loan parameters.

**Request Body:**
```json
{
  "principal": "100000.00",
  "annual_rate": "9.0",
  "tenure_months": 12
}
```

**Response:**
```json
{
  "emi_amount": "8745.23",
  "total_interest": "4942.76",
  "total_payment": "104942.76"
}
```

#### Validate Schedule

```
POST /loans/validate-schedule
```

Validate schedule integrity.

**Request Body:**
```json
{
  "account_id": "uuid"
}
```

**Response:**
```json
{
  "is_valid": true,
  "issues": []
}
```

#### Get Loan Summary

```
GET /loans/summary
```

Get summary of all loans in workspace.

**Response:**
```json
{
  "total_loans": 3,
  "total_outstanding": "1500000.00",
  "total_monthly_emi": "50000.00",
  "accounts": [
    {
      "id": "uuid",
      "name": "Home Loan",
      "balance": "-1000000.00"
    }
  ]
}
```

#### Calculate Prepayment Savings

```
POST /loans/calculate-savings
```

Calculate interest savings from prepayment.

**Request Body:**
```json
{
  "remaining_principal": "80000.00",
  "annual_rate": "9.0",
  "remaining_months": 24,
  "prepayment_amount": "20000.00"
}
```

**Response:**
```json
{
  "interest_saved_reduce_emi": "5000.00",
  "interest_saved_reduce_tenure": "7500.00",
  "months_saved_reduce_tenure": 6,
  "new_emi_reduce_emi": "3200.00",
  "new_tenure_reduce_tenure": 18
}
```

## Error Responses

All endpoints may return the following error responses:

- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error

Error response format:
```json
{
  "detail": "Error message describing the issue"
}
```
