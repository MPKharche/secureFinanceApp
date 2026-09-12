# India reseed — file list (no git commit)

## New
- `scripts/seed_demo_alex_india.py` — wipe+seed India persona (INR), loans, combined plan
- `scripts/seed_demo_india_result.json` — run artifact (counts, loan IDs, KPIs)

## Updated
- `scripts/DEMO_SESSION_NOTES.md` — India persona, verify steps, loan IDs

## Unchanged (legacy USD; do not re-run for India)
- `scripts/seed_demo_alex.py`
- `scripts/seed_loans_alex.py`
- `scripts/seed_loan_combined_plan.py`
- `scripts/seed_demo_result.json`, `seed_loans_result.json`, `seed_loan_combined_result.json`
- `scripts/alex_demo_backup.json`, `scripts/alex_transactions_export.csv`

## DB-only (via API; not in git)
- Wiped USD demo entities; reseeding INR accounts/txs/budgets/goals/assets/recurring/rules/loans/commitment
- Workspace currency INR; user preferences currency_display INR
- User alex.rivera.demo@example.com retained
