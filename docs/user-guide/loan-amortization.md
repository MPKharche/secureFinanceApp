# Loan Amortization User Guide

This guide explains how to use the loan amortization features to track and manage your loans.

## Overview

The loan amortization feature helps you:
- Track loan schedules with EMI breakdown (principal vs interest)
- Make and simulate prepayments
- Link loan payments to schedule entries automatically
- Analyze loan progress and payment history
- Monitor upcoming payments and receive alerts

## Getting Started

### Creating a Loan Account

1. Navigate to **Accounts** > **Add Account**
2. Select **Liability** as the account type
3. Select **Loan** as the subtype
4. Enter the loan details:
   - Account name (e.g., "Home Loan")
   - Current balance (negative value, e.g., -1000000)
   - Currency

### Generating the Amortization Schedule

After creating a loan account:

1. Go to the loan detail page
2. Click **Generate Schedule** (or use the regenerate endpoint)
3. Enter the loan parameters:
   - **Principal Amount**: Original loan amount
   - **Annual Interest Rate**: Rate in percentage (e.g., 8.5 for 8.5%)
   - **Tenure**: Number of months
   - **Start Date**: First EMI due date
4. Click **Generate**

The system will create a complete amortization schedule showing:
- EMI number
- Due date
- Principal component
- Interest component
- Total EMI amount
- Opening and closing balances
- Payment status

## Managing Your Loan Schedule

### Viewing the Schedule

Navigate to **Loans** > Select your loan to view:
- **Schedule Tab**: Complete amortization schedule with filters
- **Analytics Tab**: Visual charts and payment breakdown

### Filtering the Schedule

Use filters to view specific entries:
- **Status**: Filter by `scheduled`, `paid`, `partial`, `missed`, or `skipped`
- **Date Range**: View entries between specific dates

### Marking Payments

When you make a payment, mark the EMI as paid:

1. Find the EMI entry in the schedule
2. Click the status dropdown
3. Select **Paid** (or **Partial** if partial payment)

The system updates your loan progress automatically.

### Bulk Operations

Mark multiple payments at once:

1. Click **Bulk Actions** in the schedule view
2. Select multiple entries using checkboxes
3. Choose **Mark as Paid** from the actions menu

## Making Prepayments

Prepayments reduce your total interest burden. You have two options:

### Simulating a Prepayment

Before making a prepayment, simulate the impact:

1. Click **Make Prepayment** on the loan detail page
2. Enter the prepayment amount
3. Click **Simulate**

The system shows two options:
- **Reduce EMI**: Same tenure, lower monthly payment
- **Reduce Tenure**: Same EMI, shorter loan period

Compare the interest savings for each option.

### Recording a Prepayment

After deciding:

1. Select your preferred option (Reduce EMI or Reduce Tenure)
2. Click **Confirm Prepayment**
3. The system:
   - Records the prepayment
   - Creates a new schedule version
   - Preserves the old schedule for history

Your loan overview updates to reflect the new terms.

## Transaction Linking

### Auto-Linking

The system can automatically link your payment transactions to EMI entries:

1. Go to **Loans** > **Link Transactions**
2. Click **Auto-Link**
3. Set tolerance parameters:
   - **Date Tolerance**: Days before/after due date (e.g., 3 days)
   - **Amount Tolerance**: Percentage difference allowed (e.g., 2%)
4. Click **Find Matches**

The system shows potential matches with confidence levels:
- **Exact**: Same date and amount
- **High**: Within date tolerance, exact amount
- **Medium**: Within both tolerances
- **Low**: Outside tolerances but close

Review and approve suggested links.

### Manual Linking

To manually link a transaction:

1. Find the EMI entry in the schedule
2. Click **Link Transaction**
3. Select the transaction from the list
4. Click **Confirm**

## Analytics and Insights

### Loan Overview

The overview shows:
- **Progress**: Percentage of loan paid
- **EMIs Paid/Remaining**: Count of installments
- **Principal Paid/Remaining**: Amount breakdown
- **Interest Paid/Remaining**: Amount breakdown
- **Total Prepayments**: Sum of all prepayments

### Payment Breakdown

View your payment history by:
- **Year**: Annual summary
- **Quarter**: Quarterly summary
- **Month**: Monthly details

Each period shows:
- Principal paid
- Interest paid
- Total amount paid
- Prepayments made

### Debt Health Metrics

Access financial health insights:
- **Debt-to-Income Ratio**: Total outstanding vs monthly income
- **EMI-to-Income Ratio**: Monthly EMI vs monthly income
- **Weighted Average Rate**: Average interest rate across all loans
- **Health Status**: Overall debt health (Healthy, Moderate, High Risk)

### Dashboard

The loan dashboard provides:
- **Upcoming Payments**: EMIs due in the next 7 days
- **Recent Payments**: Latest payment activity
- **Alerts**: Important notifications (missed payments, high debt ratio)
- **Summary Stats**: Total outstanding and monthly EMI across all loans

## Schedule Management

### Updating Due Dates

If your EMI date changes:

**Single Entry:**
1. Click on the EMI entry
2. Edit the due date
3. Save changes

**Bulk Update:**
1. Click **Bulk Actions**
2. Select **Update Dates**
3. Choose:
   - **Shift Days**: Move all dates by X days
   - **Change Day**: Change EMI day to specific day of month
4. Specify starting EMI number
5. Apply changes

### Regenerating Schedule

If loan terms change (interest rate revision, restructuring):

1. Go to loan detail page
2. Click **Regenerate Schedule**
3. Enter new parameters:
   - From which EMI number to regenerate
   - New principal amount
   - New interest rate
   - New tenure
4. Confirm regeneration

The system creates a new schedule version and preserves the old one.

## Exporting Data

### Single Loan Export

Export a loan schedule as CSV:

1. Go to loan detail page
2. Click **Export** > **CSV**
3. File downloads with all schedule details

### Bulk Export

Export multiple loans at once:

1. Go to **Loans** overview
2. Select loans using checkboxes
3. Click **Bulk Actions** > **Export**
4. Download ZIP file containing CSV for each loan

## Utilities

### EMI Calculator

Calculate EMI before creating a loan:

1. Go to **Loans** > **EMI Calculator**
2. Enter:
   - Principal amount
   - Annual interest rate
   - Tenure in months
3. View:
   - Monthly EMI amount
   - Total interest
   - Total payment amount

### Prepayment Savings Calculator

Calculate potential savings:

1. Go to **Loans** > **Savings Calculator**
2. Enter:
   - Remaining principal
   - Interest rate
   - Remaining months
   - Prepayment amount
3. Compare savings for both methods

### Schedule Validation

Verify schedule integrity after manual edits:

1. Go to loan detail page
2. Click **Actions** > **Validate Schedule**
3. System checks:
   - Balance continuity
   - EMI component sums
   - Opening/closing balance links

Any issues are highlighted for correction.

## Best Practices

### Regular Updates

- Mark payments promptly after making them
- Review upcoming payments weekly
- Link transactions regularly for accurate tracking

### Prepayment Strategy

- Simulate before prepaying to compare options
- Consider reduce_tenure for maximum interest savings
- Make prepayments early in the loan term for best impact

### Data Accuracy

- Validate schedule after manual edits
- Regenerate schedule if terms change
- Keep transaction links up to date

### Monitoring

- Check dashboard regularly for alerts
- Review debt health metrics monthly
- Export data for record-keeping

## Troubleshooting

### Schedule Not Generated

**Issue**: Schedule generation fails or shows errors

**Solutions**:
- Verify all required fields are filled
- Check that principal and tenure are positive numbers
- Ensure date is valid and in the future
- Try regenerating from EMI 1

### Auto-Link Not Finding Matches

**Issue**: Auto-link returns no matches despite having transactions

**Solutions**:
- Increase date tolerance (try 5-7 days)
- Increase amount tolerance (try 5%)
- Check that transactions are in the same currency
- Verify transaction dates are near EMI due dates
- Use manual linking as fallback

### Prepayment Not Reducing Interest

**Issue**: Prepayment recorded but interest not reduced significantly

**Explanation**:
- Interest savings depend on timing (earlier = more savings)
- Choose reduce_tenure method for maximum savings
- Small prepayments on large loans may show modest savings
- Check the simulation to verify expected savings

### Balance Mismatch After Edits

**Issue**: Schedule validation shows balance mismatch

**Solutions**:
- Use the validation tool to identify problematic entries
- Regenerate schedule instead of manual edits
- Ensure EMI components (principal + interest) sum correctly
- Check opening balance of next entry matches closing balance of previous

### Dashboard Not Showing Loans

**Issue**: Loan dashboard appears empty

**Solutions**:
- Verify loan account type is set to "liability" with subtype "loan"
- Check that workspace filter is correct
- Ensure schedule has been generated
- Refresh the page

## Frequently Asked Questions

**Q: Can I have multiple schedules for one loan?**

A: Yes, the system maintains version history. Each prepayment or regeneration creates a new version while preserving previous versions.

**Q: What happens to old schedules after regeneration?**

A: Old schedules are preserved in the database for audit purposes. The account's `current_schedule_version` field tracks the active version.

**Q: Can I reverse a prepayment?**

A: Prepayments cannot be automatically reversed. You would need to manually regenerate the schedule with the original terms.

**Q: How accurate is the auto-linking confidence?**

A: 
- **Exact**: 100% match (same date, same amount)
- **High**: Very likely match (within date tolerance, exact amount)
- **Medium**: Probably correct (within both tolerances)
- **Low**: Review carefully (outside one or both tolerances)

**Q: Can I track loans in different currencies?**

A: Yes, each loan is tracked in its own currency. The dashboard summary converts to your workspace default currency for aggregation.

**Q: What's the difference between missed and skipped?**

A: 
- **Missed**: EMI due date passed without payment
- **Skipped**: EMI intentionally not paid (restructuring, moratorium)

**Q: How do I handle a loan moratorium?**

A: Mark affected EMIs as "skipped" and regenerate the schedule from the moratorium end date with extended tenure.

**Q: Can I import an existing schedule?**

A: Currently, schedules must be generated using the regenerate endpoint. You can then manually adjust entries if needed.

## Support

For additional help:
- Check the API documentation for technical details
- Review integration tests for usage examples
- Contact support for account-specific issues
