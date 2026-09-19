# Loan Seed Scripts - Usage Guide

This directory contains seed scripts for creating demo/test loan data in the application.

## ⚠️ IMPORTANT - Privacy & Security

**NEVER commit real user data to Git!**

- ✅ Seed scripts with configurable parameters (generic)
- ✅ Documentation with placeholder/example data
- ❌ Real loan account numbers
- ❌ Real names, emails, addresses
- ❌ Actual financial statements or PDFs
- ❌ Result JSON files with real data

Files excluded via `.gitignore`:
- `data/user-docs/` - All user documents
- `*_result.json` - Script output files
- `*_extracted_data.md` - OCR extraction results
- `IMPLEMENTATION_PLAN_*.md` - Plans with user info
- `IMPLEMENTATION_SUMMARY_*.md` - Summaries with user data

## Generic Loan Seed Script

### File: `seed_icici_personal_lpmum.py`

**Purpose:** Example script showing how to create a personal loan with amortization schedule.

**Features:**
- Configurable user email (update `USER_EMAIL`)
- Adjustable loan parameters (principal, rate, tenure, EMI)
- Generates complete 60-month amortization schedule
- Creates recurring transaction for EMI reminders
- Idempotent (safe to run multiple times)

### How to Use

1. **Configure the script:**
   ```python
   # Update these variables at the top of the script
   USER_EMAIL = "demo@example.com"  # Your test user
   LOAN_ACCOUNT_NO = "DEMO12345"    # Demo account number
   PRINCIPAL = Decimal("1000000.00")  # Loan amount
   RATE = Decimal("10.70")           # Interest rate
   # ... etc
   ```

2. **Run the script:**
   ```bash
   docker compose exec backend python3 /app/scripts/seed_icici_personal_lpmum.py
   ```

3. **Check output:**
   - Result saved to: `seed_loan_result.json` (gitignored)
   - Loan created in database
   - View in UI at: `http://localhost:3000/loans/{loan_id}`

## Creating Your Own Seed Script

To create a seed script for a different loan type:

1. Copy `seed_icici_personal_lpmum.py` as template
2. Update loan parameters and calculation logic
3. Adjust amortization schedule generation if needed
4. Test with demo user before production use

### Loan Types Supported

- **Personal Loans** - Fixed EMI, reducing balance
- **Home Loans** - Long tenure, stepped EMIs (see `seed_nrp_tbpun_loan.py`)
- **Policy Loans** - Interest-only, balloon payment (see `seed_pru_a8884526_schedules.py`)

## EMI Calculation

The script uses the standard reducing balance formula:

```
EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)

Where:
  P = Principal
  r = Monthly interest rate (annual_rate / 12 / 100)
  n = Tenure in months
```

## Database Schema

### Tables Used

1. **accounts** - Loan account details
2. **loan_amortization_schedules** - EMI schedule entries
3. **recurring_transactions** - EMI reminders
4. **categories** - Loan payment category

### Key Fields

```sql
-- Account
type = 'loan'
loan_kind = 'personal' | 'home' | 'auto' | 'education'
original_principal = loan amount
interest_rate = annual rate
tenure_months = total months
emi_amount = monthly EMI
disbursed_on = loan start date
emi_day = payment day of month

-- Schedule Entry
emi_number = 1 to tenure_months
due_date = payment due date
principal_component = principal portion
interest_component = interest portion
emi_amount = total EMI
payment_status = 'scheduled' | 'paid' | 'missed'
linked_transaction_id = payment transaction (optional)
```

## Testing

After running a seed script:

1. **Verify in database:**
   ```bash
   docker compose exec postgres psql -U securo -d securo -c \
     "SELECT * FROM accounts WHERE external_id = 'YOUR_ACCOUNT_NO';"
   ```

2. **Check schedule:**
   ```bash
   docker compose exec backend python3 << 'EOF'
   import asyncio
   from sqlalchemy import select
   from app.core.database import async_session_maker
   from app.models.account import Account
   from app.models.loan_schedule import LoanAmortizationSchedule
   
   async def check():
       async with async_session_maker() as session:
           result = await session.execute(
               select(Account).where(Account.external_id == 'YOUR_ACCOUNT_NO')
           )
           loan = result.scalar_one()
           print(f"Loan: {loan.name}, EMI: ₹{loan.emi_amount}")
           
           result = await session.execute(
               select(LoanAmortizationSchedule)
               .where(LoanAmortizationSchedule.account_id == loan.id)
           )
           entries = list(result.scalars().all())
           print(f"Schedule entries: {len(entries)}")
   
   asyncio.run(check())
   EOF
   ```

3. **View in UI:**
   - Navigate to Loans section
   - Find your loan account
   - Check schedule table

## Best Practices

1. **Use demo/test users** - Never seed real user data
2. **Parameterize everything** - Make values configurable
3. **Document assumptions** - Note any calculation quirks
4. **Validate totals** - Ensure principal + interest = total payment
5. **Test idempotency** - Script should handle re-runs safely
6. **Clean up** - Remove test data when done

## Common Issues

### "User not found"
- Update `USER_EMAIL` to match an existing user
- Or create a demo user first

### "Loan already exists"
- Script is idempotent - it updates existing data
- Delete the loan first if you want fresh data

### EMI calculation mismatch
- Check disbursement date (affects first EMI)
- Verify interest rate precision
- Consider bank-specific rounding rules

## Support

For questions or issues:
1. Check existing seed scripts for examples
2. Review loan service code: `backend/app/services/loan_schedule_service.py`
3. See API docs: `backend/app/api/v1/loans.py`

---

**Remember:** This is for DEMO/TEST data only. Never commit real user information!
